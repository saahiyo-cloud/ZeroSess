from pyrogram import Client, filters
from pyrogram.types import Message

@Client.on_message(filters.command("destroy") & filters.private)
async def destroy_info(bot: Client, msg: Message):
    await msg.reply_text(
        "**🗑️ Revoke Session**\n\n"
        "If your session leaked:\n"
        "1. Open Telegram → **Settings → Privacy and Security → Active Sessions** (or **Devices**)\n"
        "2. Tap **Terminate all other sessions**\n"
        "3. Enable **Two-Step Verification** if not already\n\n"
        "This bot cannot revoke remotely — do it from your Telegram app.\n"
        "Then generate a new string with /generate."
    )
