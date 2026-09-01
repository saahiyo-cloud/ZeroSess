import time
import psutil
from pyrogram import Client, filters
from pyrogram.types import Message
from .. import config
from ..plugins.start import START_TIME

@Client.on_message(filters.command("stats") & filters.private)
async def stats_cmd(bot: Client, msg: Message):
    # owner only for detailed stats
    if config.OWNER_ID and msg.from_user.id != config.OWNER_ID:
        await msg.reply_text("🔒 Stats is owner-only.")
        return
    up = int(time.time() - START_TIME)
    h, r = divmod(up, 3600)
    m, s = divmod(r, 60)
    cpu = psutil.cpu_percent(interval=0.5)
    ram = psutil.virtual_memory().percent
    disk = psutil.disk_usage("/").percent
    await msg.reply_text(
        f"📊 **Bot Stats**\n\n"
        f"⏱ Uptime: `{h}h {m}m {s}s`\n"
        f"🧠 CPU: `{cpu}%`\n"
        f"💾 RAM: `{ram}%`\n"
        f"💽 Disk: `{disk}%`\n"
        f"🐍 Pyrogram + Telethon"
    )

@Client.on_message(filters.command("id") & filters.private)
async def id_cmd(bot: Client, msg: Message):
    await msg.reply_text(f"🆔 Your ID: `{msg.from_user.id}`\n💬 Chat ID: `{msg.chat.id}`")
