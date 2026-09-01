import time
import asyncio
from pyrogram import Client, filters
from pyrogram.types import Message, CallbackQuery
from pyrogram.enums import ParseMode

from .. import config
from ..strings import (
    START_TEXT, HELP_TEXT, ABOUT_TEXT, MUST_JOIN_TEXT,
    kb_start, kb_help_actions, kb_choose_lib, kb_must_join
)
from ..fsm import is_rate_limited

START_TIME = time.time()

def _must_join_ok(user_id: int) -> bool:
    # MUST_JOIN enforcement is done via get_chat_member check in handler
    return True

@Client.on_message(filters.command(["start", "help", "about", "ping"]))
async def cmd_handler(bot: Client, msg: Message):
    cmd = msg.text.split()[0].lstrip("/").split("@")[0].lower()
    # must_join gate
    if config.MUST_JOIN:
        try:
            ch = config.MUST_JOIN.replace("https://t.me/", "@").replace("t.me/", "@")
            if not ch.startswith("@"):
                ch = "@" + ch.lstrip("@")
            member = await bot.get_chat_member(ch, msg.from_user.id)
            if member.status in ("kicked", "left"):
                raise ValueError("not joined")
        except Exception:
            try:
                await msg.reply_text(
                    MUST_JOIN_TEXT.format(channel=config.MUST_JOIN),
                    reply_markup=kb_must_join(config.MUST_JOIN),
                    disable_web_page_preview=True
                )
                return
            except Exception:
                pass

    if cmd == "start":
        greet = "Hello" if msg.from_user.first_name else "Hi"
        await msg.reply_text(
            START_TEXT.format(greet=greet, name=msg.from_user.first_name or "there"),
            reply_markup=kb_start(),
            disable_web_page_preview=True
        )
    elif cmd == "help":
        await msg.reply_text(HELP_TEXT, reply_markup=kb_help_actions(), disable_web_page_preview=True)
    elif cmd == "about":
        support = config.SUPPORT_CHAT or "—"
        await msg.reply_text(ABOUT_TEXT.format(support=support), disable_web_page_preview=True)
    elif cmd == "ping":
        t0 = time.time()
        m = await msg.reply_text("🏓 Pinging…")
        ms = int((time.time() - t0) * 1000)
        up = int(time.time() - START_TIME)
        h, r = divmod(up, 3600)
        mm, s = divmod(r, 60)
        await m.edit_text(f"🏓 **Pong!** `{ms}ms`\n⏱ Uptime: `{h}h {mm}m {s}s`")

@Client.on_callback_query()
async def cb_handler(bot: Client, q: CallbackQuery):
    data = q.data or ""
    # Always answer to remove spinner
    try:
        await q.answer()
    except Exception:
        pass

    if data == "menu:start":
        greet = "Hello"
        await q.message.edit_text(
            START_TEXT.format(greet=greet, name=q.from_user.first_name or "there"),
            reply_markup=kb_start(),
            disable_web_page_preview=True
        )
    elif data == "menu:help":
        await q.message.edit_text(HELP_TEXT, reply_markup=kb_help_actions(), disable_web_page_preview=True)
    elif data == "menu:about":
        support = config.SUPPORT_CHAT or "—"
        # keep start kb for navigation
        await q.message.edit_text(ABOUT_TEXT.format(support=support), reply_markup=kb_start(), disable_web_page_preview=True)
    elif data == "menu:ping":
        t0 = time.time()
        await q.message.edit_text("🏓 Pinging…")
        ms = int((time.time() - t0) * 1000)
        up = int(time.time() - START_TIME)
        h, r = divmod(up, 3600)
        mm, s = divmod(r, 60)
        await q.message.edit_text(f"🏓 **Pong!** `{ms}ms`\n⏱ Uptime: `{h}h {mm}m {s}s`", reply_markup=kb_start())
    elif data == "menu:generate":
        # rate limit check on click
        limited, retry = is_rate_limited(q.from_user.id)
        if limited:
            mins = max(1, retry // 60)
            from ..strings import RATE_LIMIT_TEXT
            await q.answer(RATE_LIMIT_TEXT.format(mins=mins, count=config.RATE_LIMIT_COUNT, limit=config.RATE_LIMIT_COUNT), show_alert=True)
            return
        await q.message.edit_text(
            "**🔑 Choose Generation Mode & Library**\n\n"
            "• **👤 User Session:** For user accounts (Phone + OTP + 2FA)\n"
            "• **🤖 Bot Token Session:** For bots via BotFather token (Instant)\n\n"
            "Strings are **not** interchangeable between Pyrogram and Telethon.",
            reply_markup=kb_choose_lib()
        )
    elif data in ("gen:user:pyro", "gen:user:tele", "gen:bot:pyro", "gen:bot:tele", "gen:pyro", "gen:tele"):
        from .generate import start_wizard
        if data in ("gen:bot:pyro", "gen:bot:tele"):
            mode = "bot"
            lib = "pyrogram" if data == "gen:bot:pyro" else "telethon"
        else:
            mode = "user"
            lib = "pyrogram" if data in ("gen:user:pyro", "gen:pyro") else "telethon"
        await start_wizard(bot, q, lib=lib, mode=mode)
    elif data == "menu:cancel":
        from ..fsm import cancel_waiter
        cancel_waiter(q.from_user.id)
        from ..strings import CANCEL_TEXT
        try:
            await q.message.edit_text(CANCEL_TEXT, reply_markup=kb_start())
        except Exception:
            await q.message.reply_text(CANCEL_TEXT, reply_markup=kb_start())
    elif data == "gen:burn":
        try:
            await q.message.delete()
        except Exception:
            try:
                await q.message.edit_text("🗑️ Deleted. Generate again with /start")
            except Exception:
                pass
    # gen:continue unused but reserved
