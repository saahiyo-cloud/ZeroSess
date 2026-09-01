import asyncio
import re
from pyrogram import Client, filters
from pyrogram.types import Message, CallbackQuery
from pyrogram.enums import ParseMode

from .. import config
from ..strings import (
    STEP_API_ID, STEP_API_HASH, STEP_API_ID_BOT, STEP_API_HASH_BOT, STEP_BOT_TOKEN,
    STEP_PHONE, STEP_OTP, STEP_2FA,
    GENERATING_TEXT, SUCCESS_CAPTION, SUCCESS_CAPTION_BOT, CANCEL_TEXT, TIMEOUT_TEXT, RATE_LIMIT_TEXT,
    kb_cancel_only, kb_start, kb_after_gen, kb_choose_lib
)
from ..fsm import (
    get_lock, wait_for_text, fulfill_waiter, cancel_waiter,
    is_rate_limited, record_attempt
)
from ..generators import pyrogram_gen as P
from ..generators import telethon_gen as T
from telethon.errors import SessionPasswordNeededError

# Global message handler to fulfill waiters
@Client.on_message(filters.private & ~filters.me & ~filters.bot, group=-1)
async def _waiter_bridge(bot: Client, msg: Message):
    # ignore commands — let command handlers run first; but still fulfill if wizard active
    text = (msg.text or msg.caption or "").strip()
    if not text:
        return
    # if user is in a wizard (has waiter), fulfill
    from ..fsm import waiters
    if msg.from_user and msg.from_user.id in waiters:
        # don't fulfill with /cancel — handle separately
        if text.lower().startswith("/cancel"):
            cancel_waiter(msg.from_user.id)
            try:
                await msg.reply_text(CANCEL_TEXT, reply_markup=kb_start())
            except Exception:
                pass
            # try delete sensitive? not needed for command
            return
        fulfilled = fulfill_waiter(msg.from_user.id, text)
        if fulfilled:
            # stop propagation so wizard owns it — but still delete sensitive later in wizard
            msg.stop_propagation()

@Client.on_message(filters.command(["generate", "gen"]))
async def cmd_generate(bot: Client, msg: Message):
    limited, retry = is_rate_limited(msg.from_user.id)
    if limited:
        mins = max(1, retry // 60)
        await msg.reply_text(RATE_LIMIT_TEXT.format(mins=mins, count=config.RATE_LIMIT_COUNT, limit=config.RATE_LIMIT_COUNT))
        return
    await msg.reply_text(
        "**🔑 Choose Generation Mode & Library**\n\n"
        "• **👤 User Session:** For user accounts (Phone + OTP + 2FA)\n"
        "• **🤖 Bot Token Session:** For bots via BotFather token (Instant)\n\n"
        "Strings are **not** interchangeable between Pyrogram and Telethon.",
        reply_markup=kb_choose_lib()
    )

@Client.on_message(filters.command("cancel"))
async def cmd_cancel(bot: Client, msg: Message):
    cancel_waiter(msg.from_user.id)
    await msg.reply_text(CANCEL_TEXT, reply_markup=kb_start())

async def _ask(bot: Client, chat_id: int, user_id: int, prompt: str, timeout: int) -> str | None:
    """
    Sends prompt and waits for user text via FSM waiter.
    Returns text or None on timeout/cancel. Handles auto-cleanup of prompt message on burn.
    """
    sent = await bot.send_message(chat_id, prompt, reply_markup=kb_cancel_only(), disable_web_page_preview=True)
    text = await wait_for_text(user_id, timeout=timeout)
    if text is None:
        try:
            await sent.edit_text(TIMEOUT_TEXT.format(sec=timeout), reply_markup=kb_start())
        except Exception:
            pass
        return None
    return text

async def _try_delete(bot: Client, chat_id: int, msg_id: int):
    try:
        await bot.delete_messages(chat_id, msg_id)
    except Exception:
        pass

async def start_wizard(bot: Client, query: CallbackQuery, lib: str, mode: str = "user"):
    """
    Entry from callback.
    Runs the full wizard in the callback's chat for user account or bot token session.
    """
    user_id = query.from_user.id
    chat_id = query.message.chat.id

    # lock per user to prevent overlapping wizards
    lock = get_lock(user_id)
    if lock.locked():
        await query.answer("⚠️ You already have a running wizard. Send /cancel to abort.", show_alert=True)
        return
    async with lock:
        limited, retry = is_rate_limited(user_id)
        if limited:
            mins = max(1, retry // 60)
            await query.message.edit_text(RATE_LIMIT_TEXT.format(mins=mins, count=config.RATE_LIMIT_COUNT, limit=config.RATE_LIMIT_COUNT), reply_markup=kb_start())
            return

        step1_prompt = STEP_API_ID_BOT if mode == "bot" else STEP_API_ID
        step2_prompt = STEP_API_HASH_BOT if mode == "bot" else STEP_API_HASH

        # Edit chooser -> step 1 (set waiter then wait)
        try:
            await query.message.edit_text(step1_prompt, reply_markup=kb_cancel_only(), disable_web_page_preview=True)
        except Exception:
            pass

        # ---- Step 1: API_ID ----
        api_id_text = await wait_for_text(user_id, timeout=config.SESSION_TIMEOUT)
        if api_id_text is None:
            try:
                await query.message.edit_text(TIMEOUT_TEXT.format(sec=config.SESSION_TIMEOUT), reply_markup=kb_start())
            except Exception:
                pass
            return

        # Validate API_ID (retry loop)
        api_id = None
        t = api_id_text
        for _ in range(3):
            try:
                api_id = P.validate_api_id(t)
                break
            except P.GenError as e:
                t = await _ask(bot, chat_id, user_id, f"{e.user_msg}\n\n{step1_prompt}", config.SESSION_TIMEOUT)
                if t is None:
                    return
        if api_id is None:
            await bot.send_message(chat_id, "❌ Too many invalid attempts. Send /start to retry.", reply_markup=kb_start())
            return

        # ---- Step 2: API_HASH ----
        api_hash_text = await _ask(bot, chat_id, user_id, step2_prompt, config.SESSION_TIMEOUT)
        if api_hash_text is None:
            return
        api_hash = None
        t = api_hash_text
        for _ in range(3):
            try:
                api_hash = P.validate_api_hash(t)
                break
            except P.GenError as e:
                t = await _ask(bot, chat_id, user_id, f"{e.user_msg}\n\n{step2_prompt}", config.SESSION_TIMEOUT)
                if t is None:
                    return
        if api_hash is None:
            await bot.send_message(chat_id, "❌ Too many invalid attempts.", reply_markup=kb_start())
            return

        # ---- If Bot Token Session Mode ----
        if mode == "bot":
            bot_token_text = await _ask(bot, chat_id, user_id, STEP_BOT_TOKEN, config.SESSION_TIMEOUT)
            if bot_token_text is None:
                return
            bot_token = None
            t = bot_token_text
            for _ in range(3):
                try:
                    bot_token = P.validate_bot_token(t)
                    break
                except P.GenError as e:
                    t = await _ask(bot, chat_id, user_id, f"{e.user_msg}\n\n{STEP_BOT_TOKEN}", config.SESSION_TIMEOUT)
                    if t is None:
                        return
            if bot_token is None:
                await bot.send_message(chat_id, "❌ Too many invalid attempts. Send /start to retry.", reply_markup=kb_start())
                return

            # Purge the user's bot token message immediately
            try:
                async for m in bot.get_chat_history(chat_id, limit=5):
                    if m.from_user and m.from_user.id == user_id and m.text and m.text.strip() == bot_token_text.strip():
                        try:
                            await m.delete()
                        except Exception:
                            pass
                        break
            except Exception:
                pass

            status = await bot.send_message(chat_id, GENERATING_TEXT)
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
                try:
                    await status.delete()
                except Exception:
                    pass

                caption = SUCCESS_CAPTION_BOT.format(lib=lib_label, session=session, sec=config.AUTO_DELETE_SECONDS)
                sent = await bot.send_message(
                    chat_id,
                    caption,
                    reply_markup=kb_after_gen(),
                    disable_web_page_preview=True
                )

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
                try:
                    await status.edit_text(e.user_msg, reply_markup=kb_start())
                except Exception:
                    await bot.send_message(chat_id, e.user_msg, reply_markup=kb_start())
            except Exception as e:
                try:
                    await status.edit_text(f"❌ Bot session generation failed: `{e}`", reply_markup=kb_start())
                except Exception:
                    pass
            finally:
                if client:
                    if lib == "pyrogram":
                        await P.safe_disconnect(client)
                    else:
                        await T.safe_disconnect(client)
            return

        # ---- Step 3: Phone (User Session Mode) ----
        phone_text = await _ask(bot, chat_id, user_id, STEP_PHONE, config.SESSION_TIMEOUT)
        if phone_text is None:
            return
        phone = None
        t = phone_text
        for _ in range(3):
            try:
                phone = P.validate_phone(t)
                break
            except P.GenError as e:
                t = await _ask(bot, chat_id, user_id, f"{e.user_msg}\n\n{STEP_PHONE}", config.SESSION_TIMEOUT)
                if t is None:
                    return
        if phone is None:
            await bot.send_message(chat_id, "❌ Too many invalid attempts.", reply_markup=kb_start())
            return

        # ---- Create client & send code ----
        status = await bot.send_message(chat_id, GENERATING_TEXT)
        client = None
        phone_code_hash = None
        try:
            if lib == "pyrogram":
                client = await P.create_client(api_id, api_hash)
                phone_code_hash = await P.send_code(client, phone)
            else:
                client = await T.create_client(api_id, api_hash)
                phone_code_hash = await T.send_code(client, phone)
            try:
                await status.edit_text("📩 OTP sent to your Telegram account. Check **Telegram → Login Codes**.")
            except Exception:
                pass
            await asyncio.sleep(1)
            try:
                await status.delete()
            except Exception:
                pass
        except (P.GenError, T.GenError) as e:
            try:
                await status.edit_text(e.user_msg, reply_markup=kb_start())
            except Exception:
                await bot.send_message(chat_id, e.user_msg, reply_markup=kb_start())
            if client:
                if lib == "pyrogram":
                    await P.safe_disconnect(client)
                else:
                    await T.safe_disconnect(client)
            return
        except Exception as e:
            try:
                await status.edit_text(f"❌ Unexpected error: `{e}`", reply_markup=kb_start())
            except Exception:
                pass
            if client:
                if lib == "pyrogram":
                    await P.safe_disconnect(client)
                else:
                    await T.safe_disconnect(client)
            return

        # ---- Step 4: OTP ----
        otp_text = await _ask(bot, chat_id, user_id, STEP_OTP, config.SESSION_TIMEOUT)
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
                t = await _ask(bot, chat_id, user_id, f"{e.user_msg}\n\n{STEP_OTP}", config.SESSION_TIMEOUT)
                if t is None:
                    if lib == "pyrogram":
                        await P.safe_disconnect(client)
                    else:
                        await T.safe_disconnect(client)
                    return
        if otp is None:
            await bot.send_message(chat_id, "❌ Too many invalid OTP attempts.", reply_markup=kb_start())
            if lib == "pyrogram":
                await P.safe_disconnect(client)
            else:
                await T.safe_disconnect(client)
            return

        # ---- Sign in ----
        status2 = await bot.send_message(chat_id, "🔐 Verifying OTP…")
        needs_2fa = False
        try:
            if lib == "pyrogram":
                try:
                    await P.sign_in(client, phone, phone_code_hash, otp)
                except P.GenError as e:
                    # check if it's 2FA needed (sign_in raises SessionPasswordNeeded directly)
                    raise
                # sign_in will raise SessionPasswordNeeded on 2FA
            else:
                await T.sign_in(client, phone, phone_code_hash, otp)
            try:
                await status2.delete()
            except Exception:
                pass
        except Exception as e:
            # Detect 2FA need via exception type/name
            is_2fa = False
            if lib == "pyrogram":
                from pyrogram.errors import SessionPasswordNeeded
                is_2fa = isinstance(e, SessionPasswordNeeded)
                if is_2fa:
                    needs_2fa = True
                    try:
                        await status2.delete()
                    except Exception:
                        pass
                else:
                    # P.GenError
                    user_msg = getattr(e, "user_msg", str(e))
                    try:
                        await status2.edit_text(user_msg, reply_markup=kb_start())
                    except Exception:
                        await bot.send_message(chat_id, user_msg, reply_markup=kb_start())
                    if lib == "pyrogram":
                        await P.safe_disconnect(client)
                    else:
                        await T.safe_disconnect(client)
                    return
            else:
                is_2fa = isinstance(e, SessionPasswordNeededError)
                if is_2fa:
                    needs_2fa = True
                    try:
                        await status2.delete()
                    except Exception:
                        pass
                else:
                    user_msg = getattr(e, "user_msg", str(e))
                    try:
                        await status2.edit_text(user_msg, reply_markup=kb_start())
                    except Exception:
                        await bot.send_message(chat_id, user_msg, reply_markup=kb_start())
                    await T.safe_disconnect(client)
                    return
            if not needs_2fa:
                return

        # ---- Step 5: 2FA if needed ----
        if needs_2fa:
            pwd_text = await _ask(bot, chat_id, user_id, STEP_2FA, config.SESSION_TIMEOUT)
            if pwd_text is None:
                if lib == "pyrogram":
                    await P.safe_disconnect(client)
                else:
                    await T.safe_disconnect(client)
                return
            pwd = pwd_text.strip()
            # try delete password message immediately via recent messages purge attempt
            # Since waiter doesn't give msg id, we attempt to delete last user message by fetching history
            try:
                async for m in bot.get_chat_history(chat_id, limit=5):
                    if m.from_user and m.from_user.id == user_id and m.text and m.text.strip() == pwd_text.strip():
                        try:
                            await m.delete()
                        except Exception:
                            pass
                        break
            except Exception:
                pass
            status3 = await bot.send_message(chat_id, "🔐 Checking password…")
            try:
                if lib == "pyrogram":
                    await P.check_password(client, pwd)
                else:
                    await T.check_password(client, pwd)
                try:
                    await status3.delete()
                except Exception:
                    pass
            except (P.GenError, T.GenError) as e:
                try:
                    await status3.edit_text(e.user_msg, reply_markup=kb_start())
                except Exception:
                    await bot.send_message(chat_id, e.user_msg, reply_markup=kb_start())
                if lib == "pyrogram":
                    await P.safe_disconnect(client)
                else:
                    await T.safe_disconnect(client)
                return
            except Exception as e:
                try:
                    await status3.edit_text(f"❌ Password error: `{e}`", reply_markup=kb_start())
                except Exception:
                    pass
                if lib == "pyrogram":
                    await P.safe_disconnect(client)
                else:
                    await T.safe_disconnect(client)
                return

        # ---- Export ----
        export_status = await bot.send_message(chat_id, "📦 Exporting session string…")
        try:
            if lib == "pyrogram":
                session = await P.export_string(client)
                # send to saved messages
                lib_label = "Pyrogram v2"
                text_for_saved = f"✅ Your {lib_label} session string:\n\n`{session}`\n\n⚠️ Keep it secret!"
                await P.send_to_saved(client, text_for_saved)
            else:
                session = T.export_string(client)
                lib_label = "Telethon"
                text_for_saved = f"✅ Your {lib_label} session string:\n\n`{session}`\n\n⚠️ Keep it secret!"
                await T.send_to_saved(client, text_for_saved)
            record_attempt(user_id)
            try:
                await export_status.delete()
            except Exception:
                pass

            # deliver to user — ephemeral copy with burn
            caption = SUCCESS_CAPTION.format(lib=lib_label, session=session, sec=config.AUTO_DELETE_SECONDS)
            sent = await bot.send_message(
                chat_id,
                caption,
                reply_markup=kb_after_gen(),
                disable_web_page_preview=True
            )
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

            # try delete OTP/phone messages from history (best effort)
            try:
                count = 0
                async for m in bot.get_chat_history(chat_id, limit=20):
                    if m.from_user and m.from_user.id == user_id and m.text:
                        txt = m.text.strip()
                        # crude: delete messages that look like phone/otp/password we just handled
                        if txt == phone or txt == otp_text or txt == pwd_text if 'pwd_text' in locals() else False:
                            try:
                                await m.delete()
                                count += 1
                            except Exception:
                                pass
                            if count >= 3:
                                break
            except Exception:
                pass

        except (P.GenError, T.GenError) as e:
            try:
                await export_status.edit_text(e.user_msg, reply_markup=kb_start())
            except Exception:
                await bot.send_message(chat_id, e.user_msg, reply_markup=kb_start())
        except Exception as e:
            try:
                await export_status.edit_text(f"❌ Export failed: `{e}`", reply_markup=kb_start())
            except Exception:
                pass
        finally:
            if lib == "pyrogram":
                await P.safe_disconnect(client)
            else:
                await T.safe_disconnect(client)
