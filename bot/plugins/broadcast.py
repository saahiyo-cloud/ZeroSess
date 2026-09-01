import time
import asyncio
from pyrogram import Client, filters
from pyrogram.types import Message
from pyrogram.errors import (
    FloodWait, UserIsBlocked, InputUserDeactivated,
    UserDeactivated, PeerIdInvalid
)

from .. import config
from .. import database as db

@Client.on_message(filters.command(["broadcast", "bcast"]) & filters.private)
async def cmd_broadcast(bot: Client, msg: Message):
    # Owner-only authorization
    if not config.OWNER_ID:
        await msg.reply_text("⚠️ `OWNER_ID` is not configured in environment variables.")
        return

    if msg.from_user.id != config.OWNER_ID:
        await msg.reply_text("🔒 This command is restricted to the bot owner.")
        return

    # Check broadcast payload
    reply = msg.reply_to_message
    text_payload = ""

    # Check for arguments
    parts = msg.text.split(maxsplit=1)
    args = parts[1].strip() if len(parts) > 1 else ""

    pin = False
    if "-pin" in args:
        pin = True
        args = args.replace("-pin", "").strip()

    if not reply and not args:
        await msg.reply_text(
            "📢 **Broadcast Usage:**\n\n"
            "• **Reply to any message** (text, photo, media, buttons) with `/broadcast`\n"
            "• **Or send direct text:** `/broadcast <message>`\n"
            "• **Optional flag:** `/broadcast -pin <message>` (pins message in chats)"
        )
        return

    user_ids = await db.get_all_user_ids()
    total_users = len(user_ids)
    if total_users == 0:
        await msg.reply_text("⚠️ No users found in database to broadcast to.")
        return

    status_msg = await msg.reply_text(f"🚀 **Starting broadcast to {total_users} users…**")

    success = 0
    blocked = 0
    failed = 0
    start_time = time.time()
    last_edit = time.time()

    for i, uid in enumerate(user_ids, 1):
        try:
            if reply:
                sent = await reply.copy(chat_id=uid)
            else:
                sent = await bot.send_message(chat_id=uid, text=args, disable_web_page_preview=True)

            if pin and sent:
                try:
                    await sent.pin(both_sides=True)
                except Exception:
                    pass

            success += 1

        except (UserIsBlocked, InputUserDeactivated, UserDeactivated):
            blocked += 1
            # Clean inactive/blocked users
            asyncio.create_task(db.remove_user(uid))

        except FloodWait as e:
            await asyncio.sleep(e.value + 1)
            try:
                if reply:
                    await reply.copy(chat_id=uid)
                else:
                    await bot.send_message(chat_id=uid, text=args, disable_web_page_preview=True)
                success += 1
            except Exception:
                failed += 1

        except (PeerIdInvalid, Exception):
            failed += 1

        # Periodic live status update every 3.5 seconds
        if time.time() - last_edit >= 3.5 or i == total_users:
            elapsed = int(time.time() - start_time)
            pct = int((i / total_users) * 100)
            try:
                await status_msg.edit_text(
                    f"📢 **Broadcast in Progress ({pct}%)**\n\n"
                    f"• 👥 **Target Users:** `{total_users}`\n"
                    f"• ⏳ **Processed:** `{i}/{total_users}`\n"
                    f"• ✅ **Delivered:** `{success}`\n"
                    f"• 🚫 **Blocked / Purged:** `{blocked}`\n"
                    f"• ❌ **Failed:** `{failed}`\n"
                    f"• ⏱ **Elapsed Time:** `{elapsed}s`"
                )
                last_edit = time.time()
            except Exception:
                pass

        await asyncio.sleep(0.04)

    total_time = int(time.time() - start_time)
    await status_msg.edit_text(
        f"🎉 **Broadcast Finished!**\n\n"
        f"• 👥 **Total Target:** `{total_users}`\n"
        f"• ✅ **Successfully Delivered:** `{success}`\n"
        f"• 🚫 **Blocked / Purged:** `{blocked}`\n"
        f"• ❌ **Failed:** `{failed}`\n"
        f"• ⏱ **Total Time Taken:** `{total_time}s`"
    )
