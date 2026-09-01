import time
import psutil
from pyrogram import Client, filters
from pyrogram.types import Message
from .. import config
from .. import database as db
from ..plugins.start import START_TIME

@Client.on_message(filters.command(["stats", "status"]) & filters.private)
async def stats_cmd(bot: Client, msg: Message):
    # Owner-only detailed stats
    if config.OWNER_ID and msg.from_user.id != config.OWNER_ID:
        await msg.reply_text("🔒 `/stats` is restricted to the bot owner.")
        return

    up = int(time.time() - START_TIME)
    h, r = divmod(up, 3600)
    m, s = divmod(r, 60)
    cpu = psutil.cpu_percent(interval=0.2)
    ram = psutil.virtual_memory().percent
    disk = psutil.disk_usage("/").percent

    analytics = await db.get_analytics()

    text = (
        "📊 **ZeroSess — Analytics & System Metrics**\n\n"
        "👥 **User Base:**\n"
        f"• **Total Registered Users:** `{analytics['total_users']}`\n"
        f"• **Active in last 24h:** `{analytics['active_24h']}`\n"
        f"• **Active in last 7d:** `{analytics['active_7d']}`\n\n"
        "🔑 **Session Generation:**\n"
        f"• **Total Generated:** `{analytics['total_generations']}`\n"
        f"  ├ 🔥 **Pyrogram v2 (User):** `{analytics['pyro_generations']}`\n"
        f"  ├ ⚡ **Telethon (User):** `{analytics['tele_generations']}`\n"
        f"  └ 🤖 **Bot Token Sessions:** `{analytics['bot_generations']}`\n\n"
        "🔍 **Inspection & Quality:**\n"
        f"• **Total Sessions Checked:** `{analytics['total_checks']}`\n\n"
        "🖥️ **System Resources:**\n"
        f"• ⏱ **Uptime:** `{h}h {m}m {s}s`\n"
        f"• 🧠 **CPU Load:** `{cpu}%`\n"
        f"• 💾 **RAM Usage:** `{ram}%`\n"
        f"• 💽 **Disk Usage:** `{disk}%`"
    )

    await msg.reply_text(text)

@Client.on_message(filters.command("id") & filters.private)
async def id_cmd(bot: Client, msg: Message):
    await msg.reply_text(f"🆔 Your ID: `{msg.from_user.id}`\n💬 Chat ID: `{msg.chat.id}`")
