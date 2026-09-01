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
from .. import database as db

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

@Client.on_message(filters.command(["check", "validate", "checksession"]))
async def cmd_check(bot: Client, msg: Message):
    user_id = msg.from_user.id
    chat_id = msg.chat.id
    try:
        await msg.delete()
    except Exception:
        pass
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
            await _edit_or_send(
                bot,
                chat_id,
                callback_msg,
                RATE_LIMIT_TEXT.format(mins=mins, count=config.RATE_LIMIT_COUNT, limit=config.RATE_LIMIT_COUNT),
                reply_markup=kb_start()
            )
            return

        msg = await _edit_or_send(bot, chat_id, callback_msg, CHECK_PROMPT, reply_markup=kb_cancel_only())

        session_text = await wait_for_text(user_id, timeout=config.SESSION_TIMEOUT)
        if session_text is None:
            await _edit_or_send(bot, chat_id, msg, TIMEOUT_TEXT.format(sec=config.SESSION_TIMEOUT), reply_markup=kb_start())
            return

        session_str = session_text.strip()
        msg = await _edit_or_send(bot, chat_id, msg, "🔍 **Inspecting session string in-memory…**", None)

        try:
            result = await inspect_session(session_str)

            if result.get("valid"):
                asyncio.create_task(db.increment_metric("sessions_checked"))
                footprint = result.get("footprint", {})
                total_dialogs = footprint.get("total_dialogs", 0)
                owned_count = footprint.get("owned_count", 0)
                owned_titles = footprint.get("owned_titles", [])
                admin_count = footprint.get("admin_count", 0)
                admin_titles = footprint.get("admin_titles", [])

                owned_list = ("\n  └ " + "\n  └ ".join(owned_titles)) if owned_titles else ""
                admin_list = ("\n  └ " + "\n  └ ".join(admin_titles)) if admin_titles else ""

                text = CHECK_ACTIVE_TEXT.format(
                    lib=result["lib"],
                    acc_type=result["acc_type"],
                    name=result["name"],
                    user_id=result["user_id"],
                    username=result["username"],
                    spambot=result.get("spambot_status", "🟢 Clean (No limits applied)"),
                    dc_id=result["dc_id"],
                    dc_location=result["dc_location"],
                    is_premium=result["is_premium"],
                    total_dialogs=total_dialogs,
                    owned_count=owned_count,
                    owned_list=owned_list,
                    admin_count=admin_count,
                    admin_list=admin_list,
                    sec=config.AUTO_DELETE_SECONDS
                )
                sent_result = await _edit_or_send(
                    bot,
                    chat_id,
                    msg,
                    text,
                    reply_markup=kb_after_check()
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
                await _edit_or_send(
                    bot,
                    chat_id,
                    msg,
                    text,
                    reply_markup=kb_start()
                )

        except Exception as e:
            await _edit_or_send(bot, chat_id, msg, f"❌ Inspection failed: `{e}`", reply_markup=kb_start())
