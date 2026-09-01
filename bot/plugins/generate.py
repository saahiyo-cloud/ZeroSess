import time
import asyncio
import re
from pyrogram import Client, filters
from pyrogram.types import Message, CallbackQuery
from pyrogram.enums import ParseMode
from pyrogram.errors import SessionPasswordNeeded

from .. import config
from ..strings import (
    STEP_API_ID, STEP_API_HASH, STEP_API_ID_BOT, STEP_API_HASH_BOT,
    STEP_API_ID_QR, STEP_API_HASH_QR, STEP_BOT_TOKEN,
    STEP_PHONE, STEP_OTP, STEP_2FA, QR_PROMPT,
    GENERATING_TEXT, SUCCESS_CAPTION, SUCCESS_CAPTION_BOT, CANCEL_TEXT, TIMEOUT_TEXT, RATE_LIMIT_TEXT,
    kb_cancel_only, kb_start, kb_after_gen, kb_choose_lib, kb_step_api_id
)
from ..fsm import (
    get_lock, wait_for_text, fulfill_waiter, cancel_waiter,
    is_rate_limited, record_attempt
)
from .. import database as db
from ..generators import pyrogram_gen as P
from ..generators import telethon_gen as T
from ..generators.qr_helper import generate_qr_image, export_pyrogram_qr, check_pyrogram_qr, QRError
from telethon.errors import SessionPasswordNeededError

# Global message handler to fulfill waiters
@Client.on_message(filters.private & ~filters.me & ~filters.bot, group=-1)
async def _waiter_bridge(bot: Client, msg: Message):
    text = (msg.text or msg.caption or "").strip()
    if not text:
        return
    # if user is in a wizard (has waiter), fulfill
    from ..fsm import waiters
    if msg.from_user and msg.from_user.id in waiters:
        if text.lower().startswith("/cancel"):
            cancel_waiter(msg.from_user.id)
            try:
                await msg.delete()
            except Exception:
                pass
            try:
                await msg.reply_text(CANCEL_TEXT, reply_markup=kb_start())
            except Exception:
                pass
            return
        fulfilled = fulfill_waiter(msg.from_user.id, text)
        if fulfilled:
            # Auto cleanup user's input message immediately for privacy and clean chat
            try:
                await msg.delete()
            except Exception:
                pass
            msg.stop_propagation()

@Client.on_message(filters.command(["generate", "gen"]))
async def cmd_generate(bot: Client, msg: Message):
    limited, retry = is_rate_limited(msg.from_user.id)
    if limited:
        mins = max(1, retry // 60)
        await msg.reply_text(RATE_LIMIT_TEXT.format(mins=mins, count=config.RATE_LIMIT_COUNT, limit=config.RATE_LIMIT_COUNT))
        return
    try:
        await msg.delete()
    except Exception:
        pass
    await msg.reply_text(
        "🔑 **Choose Library & Mode**\n\n"
        "• **📷 QR Login:** Scan with Telegram app\n"
        "• **👤 Phone OTP:** Phone + OTP code\n"
        "• **🤖 Bot Token:** BotFather token\n\n"
        "Select an option below:",
        reply_markup=kb_choose_lib()
    )

@Client.on_message(filters.command("cancel"))
async def cmd_cancel(bot: Client, msg: Message):
    cancel_waiter(msg.from_user.id)
    try:
        await msg.delete()
    except Exception:
        pass
    await msg.reply_text(CANCEL_TEXT, reply_markup=kb_start())

async def _edit_or_send(bot: Client, chat_id: int, active_msg: Message | None, text: str, reply_markup=None) -> Message:
    if active_msg:
        try:
            await active_msg.edit_text(text, reply_markup=reply_markup, disable_web_page_preview=True)
            return active_msg
        except Exception:
            try:
                await active_msg.delete()
            except Exception:
                pass
    return await bot.send_message(chat_id, text, reply_markup=reply_markup, disable_web_page_preview=True)

async def _ask(bot: Client, chat_id: int, user_id: int, prompt: str, timeout: int, reply_markup=None, active_msg: Message | None = None) -> tuple[str | None, Message]:
    msg = await _edit_or_send(bot, chat_id, active_msg, prompt, reply_markup or kb_cancel_only())
    text = await wait_for_text(user_id, timeout=timeout)
    if text is None:
        try:
            await msg.edit_text(TIMEOUT_TEXT.format(sec=timeout), reply_markup=kb_start())
        except Exception:
            pass
        return None, msg
    return text, msg

async def start_wizard(bot: Client, query: CallbackQuery, lib: str, mode: str = "user"):
    """
    Entry from callback.
    Runs the full wizard in the callback's chat for user account, bot token, or QR login session.
    """
    user_id = query.from_user.id
    chat_id = query.message.chat.id
    msg = query.message

    # lock per user to prevent overlapping wizards
    lock = get_lock(user_id)
    if lock.locked():
        await query.answer("⚠️ You already have a running wizard. Send /cancel to abort.", show_alert=True)
        return
    async with lock:
        limited, retry = is_rate_limited(user_id)
        if limited:
            mins = max(1, retry // 60)
            await _edit_or_send(bot, chat_id, msg, RATE_LIMIT_TEXT.format(mins=mins, count=config.RATE_LIMIT_COUNT, limit=config.RATE_LIMIT_COUNT), reply_markup=kb_start())
            return

        if mode == "bot":
            step1_prompt = STEP_API_ID_BOT
            step2_prompt = STEP_API_HASH_BOT
        elif mode == "qr":
            step1_prompt = STEP_API_ID_QR
            step2_prompt = STEP_API_HASH_QR
        else:
            step1_prompt = STEP_API_ID
            step2_prompt = STEP_API_HASH

        # Step 1: Edit into Step 1
        msg = await _edit_or_send(bot, chat_id, msg, step1_prompt, kb_step_api_id())

        api_id_text = await wait_for_text(user_id, timeout=config.SESSION_TIMEOUT)
        if api_id_text is None:
            await _edit_or_send(bot, chat_id, msg, TIMEOUT_TEXT.format(sec=config.SESSION_TIMEOUT), reply_markup=kb_start())
            return

        api_id = None
        api_hash = None

        if api_id_text == "__DEFAULT_API__":
            api_id = config.API_ID
            api_hash = config.API_HASH
        else:
            # Validate custom API_ID (retry loop)
            t = api_id_text
            for _ in range(3):
                if t == "__DEFAULT_API__":
                    api_id = config.API_ID
                    api_hash = config.API_HASH
                    break
                try:
                    api_id = P.validate_api_id(t)
                    break
                except P.GenError as e:
                    t, msg = await _ask(bot, chat_id, user_id, f"{e.user_msg}\n\n{step1_prompt}", config.SESSION_TIMEOUT, reply_markup=kb_step_api_id(), active_msg=msg)
                    if t is None:
                        return
            if api_id is None:
                await _edit_or_send(bot, chat_id, msg, "❌ Too many invalid attempts. Send /start to retry.", reply_markup=kb_start())
                return

            if not api_hash:
                # Step 2: API_HASH
                api_hash_text, msg = await _ask(bot, chat_id, user_id, step2_prompt, config.SESSION_TIMEOUT, active_msg=msg)
                if api_hash_text is None:
                    return
                t = api_hash_text
                for _ in range(3):
                    try:
                        api_hash = P.validate_api_hash(t)
                        break
                    except P.GenError as e:
                        t, msg = await _ask(bot, chat_id, user_id, f"{e.user_msg}\n\n{step2_prompt}", config.SESSION_TIMEOUT, active_msg=msg)
                        if t is None:
                            return
                if api_hash is None:
                    await _edit_or_send(bot, chat_id, msg, "❌ Too many invalid attempts.", reply_markup=kb_start())
                    return

        # ---- If QR Login Mode ----
        if mode == "qr":
            lib_label = "Pyrogram v2" if lib == "pyrogram" else "Telethon"
            msg = await _edit_or_send(bot, chat_id, msg, "⏳ **Initializing QR Login…**", None)
            client = None
            qr_msg = None
            try:
                if lib == "pyrogram":
                    client = await P.create_client(api_id, api_hash)
                    url, expires_at = await export_pyrogram_qr(client, api_id, api_hash)
                    if not url:
                        raise QRError("❌ Could not generate QR token.")
                    qr_buf = generate_qr_image(url)
                    try:
                        await msg.delete()
                    except Exception:
                        pass
                    qr_msg = await bot.send_photo(
                        chat_id,
                        photo=qr_buf,
                        caption=QR_PROMPT.format(lib=lib_label),
                        reply_markup=kb_cancel_only()
                    )

                    scanned = False
                    needs_2fa = False
                    start_t = time.time()
                    while time.time() - start_t < 120:
                        await asyncio.sleep(2.5)
                        try:
                            if await check_pyrogram_qr(client, api_id, api_hash):
                                scanned = True
                                break
                        except SessionPasswordNeeded:
                            scanned = True
                            needs_2fa = True
                            break
                        except Exception:
                            pass
                        # Refresh QR if expiring
                        if time.time() >= expires_at - 2:
                            try:
                                url, expires_at = await export_pyrogram_qr(client, api_id, api_hash)
                                if url:
                                    qr_buf = generate_qr_image(url)
                                    try:
                                        await qr_msg.delete()
                                    except Exception:
                                        pass
                                    qr_msg = await bot.send_photo(
                                        chat_id,
                                        photo=qr_buf,
                                        caption=QR_PROMPT.format(lib=lib_label),
                                        reply_markup=kb_cancel_only()
                                    )
                            except Exception:
                                pass
                else:
                    # Telethon QR Login
                    client = await T.create_client(api_id, api_hash)
                    qr_login = await client.qr_login()
                    qr_buf = generate_qr_image(qr_login.url)
                    try:
                        await msg.delete()
                    except Exception:
                        pass
                    qr_msg = await bot.send_photo(
                        chat_id,
                        photo=qr_buf,
                        caption=QR_PROMPT.format(lib=lib_label),
                        reply_markup=kb_cancel_only()
                    )

                    scanned = False
                    needs_2fa = False
                    start_t = time.time()
                    while time.time() - start_t < 120:
                        try:
                            await qr_login.wait(timeout=15)
                            scanned = True
                            break
                        except asyncio.TimeoutError:
                            try:
                                await qr_login.recreate()
                                qr_buf = generate_qr_image(qr_login.url)
                                try:
                                    await qr_msg.delete()
                                except Exception:
                                    pass
                                qr_msg = await bot.send_photo(
                                    chat_id,
                                    photo=qr_buf,
                                    caption=QR_PROMPT.format(lib=lib_label),
                                    reply_markup=kb_cancel_only()
                                )
                            except Exception:
                                pass
                        except SessionPasswordNeededError:
                            scanned = True
                            needs_2fa = True
                            break

                if qr_msg:
                    try:
                        await qr_msg.delete()
                    except Exception:
                        pass

                if not scanned:
                    await bot.send_message(chat_id, "⏰ QR Login expired. Send /generate to retry.", reply_markup=kb_start())
                    if client:
                        if lib == "pyrogram":
                            await P.safe_disconnect(client)
                        else:
                            await T.safe_disconnect(client)
                    return

                # If 2FA password needed
                if needs_2fa:
                    pwd_text, msg = await _ask(bot, chat_id, user_id, STEP_2FA, config.SESSION_TIMEOUT, active_msg=None)
                    if pwd_text is None:
                        if lib == "pyrogram":
                            await P.safe_disconnect(client)
                        else:
                            await T.safe_disconnect(client)
                        return
                    pwd = pwd_text.strip()
                    msg = await _edit_or_send(bot, chat_id, msg, "🔐 Checking password…", None)
                    try:
                        if lib == "pyrogram":
                            await P.check_password(client, pwd)
                        else:
                            await T.check_password(client, pwd)
                    except (P.GenError, T.GenError) as e:
                        await _edit_or_send(bot, chat_id, msg, e.user_msg, reply_markup=kb_start())
                        if lib == "pyrogram":
                            await P.safe_disconnect(client)
                        else:
                            await T.safe_disconnect(client)
                        return

                # Export string
                msg = await bot.send_message(chat_id, "📦 Exporting session string…")
                if lib == "pyrogram":
                    session = await P.export_string(client)
                    text_for_saved = f"✅ Your {lib_label} session string:\n\n`{session}`\n\n⚠️ Keep it secret!"
                    await P.send_to_saved(client, text_for_saved)
                else:
                    session = T.export_string(client)
                    text_for_saved = f"✅ Your {lib_label} session string:\n\n`{session}`\n\n⚠️ Keep it secret!"
                    await T.send_to_saved(client, text_for_saved)

                record_attempt(user_id)
                asyncio.create_task(db.increment_metric("sessions_generated"))
                if lib == "pyrogram":
                    asyncio.create_task(db.increment_metric("sessions_pyro"))
                else:
                    asyncio.create_task(db.increment_metric("sessions_tele"))

                caption = SUCCESS_CAPTION.format(lib=lib_label, session=session, sec=config.AUTO_DELETE_SECONDS)
                sent = await _edit_or_send(bot, chat_id, msg, caption, reply_markup=kb_after_gen())

                async def _autoburn_qr():
                    await asyncio.sleep(config.AUTO_DELETE_SECONDS)
                    try:
                        await sent.delete()
                    except Exception:
                        pass
                    try:
                        await bot.send_message(chat_id, "🗑️ Previous session message auto-deleted for security.", reply_markup=kb_start())
                    except Exception:
                        pass
                asyncio.create_task(_autoburn_qr())

            except (P.GenError, T.GenError, QRError) as e:
                if qr_msg:
                    try:
                        await qr_msg.delete()
                    except Exception:
                        pass
                user_msg = getattr(e, "user_msg", str(e))
                await bot.send_message(chat_id, user_msg, reply_markup=kb_start())
            except Exception as e:
                if qr_msg:
                    try:
                        await qr_msg.delete()
                    except Exception:
                        pass
                await bot.send_message(chat_id, f"❌ QR Login failed: `{e}`", reply_markup=kb_start())
            finally:
                if client:
                    if lib == "pyrogram":
                        await P.safe_disconnect(client)
                    else:
                        await T.safe_disconnect(client)
            return

        # ---- If Bot Token Session Mode ----
        if mode == "bot":
            bot_token_text, msg = await _ask(bot, chat_id, user_id, STEP_BOT_TOKEN, config.SESSION_TIMEOUT, active_msg=msg)
            if bot_token_text is None:
                return
            bot_token = None
            t = bot_token_text
            for _ in range(3):
                try:
                    bot_token = P.validate_bot_token(t)
                    break
                except P.GenError as e:
                    t, msg = await _ask(bot, chat_id, user_id, f"{e.user_msg}\n\n{STEP_BOT_TOKEN}", config.SESSION_TIMEOUT, active_msg=msg)
                    if t is None:
                        return
            if bot_token is None:
                await _edit_or_send(bot, chat_id, msg, "❌ Too many invalid attempts. Send /start to retry.", reply_markup=kb_start())
                return

            msg = await _edit_or_send(bot, chat_id, msg, GENERATING_TEXT, None)
            client = None
            try:
                if lib == "pyrogram":
                    client = await P.create_client(api_id, api_hash)
                    await P.sign_in_bot(client, bot_token)
                    session = await P.export_string(client)
                    lib_label = "Pyrogram v2 (Bot)"
                else:
                    client = await T.create_client(api_id, api_hash)
                    await T.sign_in_bot(client, bot_token)
                    session = T.export_string(client)
                    lib_label = "Telethon (Bot)"

                record_attempt(user_id)
                asyncio.create_task(db.increment_metric("sessions_generated"))
                asyncio.create_task(db.increment_metric("sessions_bot"))

                caption = SUCCESS_CAPTION_BOT.format(lib=lib_label, session=session, sec=config.AUTO_DELETE_SECONDS)
                sent = await _edit_or_send(bot, chat_id, msg, caption, reply_markup=kb_after_gen())

                async def _autoburn_bot():
                    await asyncio.sleep(config.AUTO_DELETE_SECONDS)
                    try:
                        await sent.delete()
                    except Exception:
                        pass
                    try:
                        await bot.send_message(chat_id, "🗑️ Previous bot session message auto-deleted for security.", reply_markup=kb_start())
                    except Exception:
                        pass
                asyncio.create_task(_autoburn_bot())

            except (P.GenError, T.GenError) as e:
                await _edit_or_send(bot, chat_id, msg, e.user_msg, reply_markup=kb_start())
            except Exception as e:
                await _edit_or_send(bot, chat_id, msg, f"❌ Bot session generation failed: `{e}`", reply_markup=kb_start())
            finally:
                if client:
                    if lib == "pyrogram":
                        await P.safe_disconnect(client)
                    else:
                        await T.safe_disconnect(client)
            return

        # ---- Step 3: Phone (User Session Mode) ----
        phone_text, msg = await _ask(bot, chat_id, user_id, STEP_PHONE, config.SESSION_TIMEOUT, active_msg=msg)
        if phone_text is None:
            return
        phone = None
        t = phone_text
        for _ in range(3):
            try:
                phone = P.validate_phone(t)
                break
            except P.GenError as e:
                t, msg = await _ask(bot, chat_id, user_id, f"{e.user_msg}\n\n{STEP_PHONE}", config.SESSION_TIMEOUT, active_msg=msg)
                if t is None:
                    return
        if phone is None:
            await _edit_or_send(bot, chat_id, msg, "❌ Too many invalid attempts.", reply_markup=kb_start())
            return

        # ---- Create client & send code ----
        msg = await _edit_or_send(bot, chat_id, msg, "⏳ Sending OTP to your Telegram account…", None)
        client = None
        phone_code_hash = None
        try:
            if lib == "pyrogram":
                client = await P.create_client(api_id, api_hash)
                phone_code_hash = await P.send_code(client, phone)
            else:
                client = await T.create_client(api_id, api_hash)
                phone_code_hash = await T.send_code(client, phone)
        except (P.GenError, T.GenError) as e:
            await _edit_or_send(bot, chat_id, msg, e.user_msg, reply_markup=kb_start())
            if client:
                if lib == "pyrogram":
                    await P.safe_disconnect(client)
                else:
                    await T.safe_disconnect(client)
            return
        except Exception as e:
            await _edit_or_send(bot, chat_id, msg, f"❌ Unexpected error: `{e}`", reply_markup=kb_start())
            if client:
                if lib == "pyrogram":
                    await P.safe_disconnect(client)
                else:
                    await T.safe_disconnect(client)
            return

        # ---- Step 4: OTP ----
        otp_text, msg = await _ask(bot, chat_id, user_id, STEP_OTP, config.SESSION_TIMEOUT, active_msg=msg)
        if otp_text is None:
            if lib == "pyrogram":
                await P.safe_disconnect(client)
            else:
                await T.safe_disconnect(client)
            return
        otp = None
        t = otp_text
        for _ in range(3):
            try:
                otp = P.normalize_otp(t)
                break
            except P.GenError as e:
                t, msg = await _ask(bot, chat_id, user_id, f"{e.user_msg}\n\n{STEP_OTP}", config.SESSION_TIMEOUT, active_msg=msg)
                if t is None:
                    if lib == "pyrogram":
                        await P.safe_disconnect(client)
                    else:
                        await T.safe_disconnect(client)
                    return
        if otp is None:
            await _edit_or_send(bot, chat_id, msg, "❌ Too many invalid OTP attempts.", reply_markup=kb_start())
            if lib == "pyrogram":
                await P.safe_disconnect(client)
            else:
                await T.safe_disconnect(client)
            return

        # ---- Sign in ----
        msg = await _edit_or_send(bot, chat_id, msg, "🔐 Verifying OTP…", None)
        needs_2fa = False
        try:
            if lib == "pyrogram":
                try:
                    await P.sign_in(client, phone, phone_code_hash, otp)
                except P.GenError:
                    raise
            else:
                await T.sign_in(client, phone, phone_code_hash, otp)
        except Exception as e:
            # Detect 2FA need
            is_2fa = False
            if lib == "pyrogram":
                from pyrogram.errors import SessionPasswordNeeded
                is_2fa = isinstance(e, SessionPasswordNeeded)
                if is_2fa:
                    needs_2fa = True
                else:
                    user_msg = getattr(e, "user_msg", str(e))
                    await _edit_or_send(bot, chat_id, msg, user_msg, reply_markup=kb_start())
                    await P.safe_disconnect(client)
                    return
            else:
                is_2fa = isinstance(e, SessionPasswordNeededError)
                if is_2fa:
                    needs_2fa = True
                else:
                    user_msg = getattr(e, "user_msg", str(e))
                    await _edit_or_send(bot, chat_id, msg, user_msg, reply_markup=kb_start())
                    await T.safe_disconnect(client)
                    return
            if not needs_2fa:
                return

        # ---- Step 5: 2FA if needed ----
        if needs_2fa:
            pwd_text, msg = await _ask(bot, chat_id, user_id, STEP_2FA, config.SESSION_TIMEOUT, active_msg=msg)
            if pwd_text is None:
                if lib == "pyrogram":
                    await P.safe_disconnect(client)
                else:
                    await T.safe_disconnect(client)
                return
            pwd = pwd_text.strip()
            msg = await _edit_or_send(bot, chat_id, msg, "🔐 Checking password…", None)
            try:
                if lib == "pyrogram":
                    await P.check_password(client, pwd)
                else:
                    await T.check_password(client, pwd)
            except (P.GenError, T.GenError) as e:
                await _edit_or_send(bot, chat_id, msg, e.user_msg, reply_markup=kb_start())
                if lib == "pyrogram":
                    await P.safe_disconnect(client)
                else:
                    await T.safe_disconnect(client)
                return
            except Exception as e:
                await _edit_or_send(bot, chat_id, msg, f"❌ Password error: `{e}`", reply_markup=kb_start())
                if lib == "pyrogram":
                    await P.safe_disconnect(client)
                else:
                    await T.safe_disconnect(client)
                return

        # ---- Export ----
        msg = await _edit_or_send(bot, chat_id, msg, "📦 Exporting session string…", None)
        try:
            if lib == "pyrogram":
                session = await P.export_string(client)
                lib_label = "Pyrogram v2"
                text_for_saved = f"✅ Your {lib_label} session string:\n\n`{session}`\n\n⚠️ Keep it secret!"
                await P.send_to_saved(client, text_for_saved)
            else:
                session = T.export_string(client)
                lib_label = "Telethon"
                text_for_saved = f"✅ Your {lib_label} session string:\n\n`{session}`\n\n⚠️ Keep it secret!"
                await T.send_to_saved(client, text_for_saved)
            record_attempt(user_id)
            asyncio.create_task(db.increment_metric("sessions_generated"))
            if lib == "pyrogram":
                asyncio.create_task(db.increment_metric("sessions_pyro"))
            else:
                asyncio.create_task(db.increment_metric("sessions_tele"))

            # deliver to user
            caption = SUCCESS_CAPTION.format(lib=lib_label, session=session, sec=config.AUTO_DELETE_SECONDS)
            sent = await _edit_or_send(bot, chat_id, msg, caption, reply_markup=kb_after_gen())

            # auto-burn schedule
            async def _autoburn():
                await asyncio.sleep(config.AUTO_DELETE_SECONDS)
                try:
                    await sent.delete()
                except Exception:
                    pass
                try:
                    await bot.send_message(chat_id, "🗑️ Previous session message auto-deleted for security.", reply_markup=kb_start())
                except Exception:
                    pass
            asyncio.create_task(_autoburn())

        except (P.GenError, T.GenError) as e:
            await _edit_or_send(bot, chat_id, msg, e.user_msg, reply_markup=kb_start())
        except Exception as e:
            await _edit_or_send(bot, chat_id, msg, f"❌ Export failed: `{e}`", reply_markup=kb_start())
        finally:
            if lib == "pyrogram":
                await P.safe_disconnect(client)
            else:
                await T.safe_disconnect(client)
