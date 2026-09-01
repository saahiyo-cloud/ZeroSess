from pyrogram import Client, filters
from pyrogram.types import Message

@Client.on_message(filters.command("destroy") & filters.private)
async def destroy_info(bot: Client, msg: Message):
    try:
        await msg.delete()
    except Exception:
        pass
    await msg.reply_text(
        "🗑️ **How to Revoke Sessions**\n\n"
        "1. Open **Telegram → Settings → Devices**\n"
        "2. Tap **Terminate all other sessions**\n"
        "3. Enable **Two-Step Verification (2FA)**\n\n"
        "Then generate a new string with /generate."
    )
