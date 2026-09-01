import asyncio
from pyrogram import Client, filters
from pyrogram.types import Message, CallbackQuery

from .. import config
from ..strings import (
    CHECK_PROMPT, CHECK_ACTIVE_TEXT, CHECK_INVALID_TEXT,
    kb_cancel_only, kb_start, kb_after_check, TIMEOUT_TEXT
)
from ..fsm import get_lock, wait_for_text, is_rate_limited
from ..generators.checker import inspect_session

@Client.on_message(filters.command(["check", "validate", "checksession"]))
async def cmd_check(bot: Client, msg: Message):
    user_id = msg.from_user.id
    chat_id = msg.chat.id
    await run_check_flow(bot, chat_id, user_id)

async def handle_check_callback(bot: Client, query: CallbackQuery):
    user_id = query.from_user.id
    chat_id = query.message.chat.id
    await run_check_flow(bot, chat_id, user_id, callback_msg=query.message)

async def run_check_flow(bot: Client, chat_id: int, user_id: int, callback_msg: Message | None = None):
    lock = get_lock(user_id)
    if lock.locked():
        if callback_msg:
            try:
                await bot.send_message(chat_id, "⚠️ A process is already running. Send /cancel to abort.")
            except Exception:
                pass
        return

    async with lock:
        limited, retry = is_rate_limited(user_id)
        if limited:
            mins = max(1, retry // 60)
            from ..strings import RATE_LIMIT_TEXT
            await bot.send_message(
                chat_id,
                RATE_LIMIT_TEXT.format(mins=mins, count=config.RATE_LIMIT_COUNT, limit=config.RATE_LIMIT_COUNT),
                reply_markup=kb_start()
            )
            return

        if callback_msg:
            try:
                sent = await callback_msg.edit_text(CHECK_PROMPT, reply_markup=kb_cancel_only(), disable_web_page_preview=True)
            except Exception:
                sent = await bot.send_message(chat_id, CHECK_PROMPT, reply_markup=kb_cancel_only(), disable_web_page_preview=True)
        else:
            sent = await bot.send_message(chat_id, CHECK_PROMPT, reply_markup=kb_cancel_only(), disable_web_page_preview=True)

        session_text = await wait_for_text(user_id, timeout=config.SESSION_TIMEOUT)
        if session_text is None:
            try:
                await sent.edit_text(TIMEOUT_TEXT.format(sec=config.SESSION_TIMEOUT), reply_markup=kb_start())
            except Exception:
                pass
            return

        session_str = session_text.strip()

        # Immediate purge of user input containing sensitive session string
        try:
            async for m in bot.get_chat_history(chat_id, limit=5):
                if m.from_user and m.from_user.id == user_id and m.text and m.text.strip() == session_str:
                    try:
                        await m.delete()
                    except Exception:
                        pass
                    break
        except Exception:
            pass

        inspect_msg = await bot.send_message(chat_id, "🔍 **Inspecting session string in-memory…**")

        try:
            result = await inspect_session(session_str)
            try:
                await inspect_msg.delete()
            except Exception:
                pass

            if result.get("valid"):
                text = CHECK_ACTIVE_TEXT.format(
                    lib=result["lib"],
                    acc_type=result["acc_type"],
                    name=result["name"],
                    user_id=result["user_id"],
                    username=result["username"],
                    dc_id=result["dc_id"],
                    dc_location=result["dc_location"],
                    is_premium=result["is_premium"],
                    sec=config.AUTO_DELETE_SECONDS
                )
                sent_result = await bot.send_message(
                    chat_id,
                    text,
                    reply_markup=kb_after_check(),
                    disable_web_page_preview=True
                )

                # Auto-burn inspection result
                async def _autoburn():
                    await asyncio.sleep(config.AUTO_DELETE_SECONDS)
                    try:
                        await sent_result.delete()
                    except Exception:
                        pass
                asyncio.create_task(_autoburn())

            else:
                reason = result.get("reason", "Unknown error")
                text = CHECK_INVALID_TEXT.format(reason=reason)
                await bot.send_message(
                    chat_id,
                    text,
                    reply_markup=kb_start(),
                    disable_web_page_preview=True
                )

        except Exception as e:
            try:
                await inspect_msg.edit_text(f"❌ Inspection failed: `{e}`", reply_markup=kb_start())
            except Exception:
                pass
