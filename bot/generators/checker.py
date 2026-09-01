import asyncio
from pyrogram import Client
from pyrogram.enums import ChatType
from pyrogram.errors import (
    AuthKeyUnregistered, UserDeactivated, SessionRevoked,
    AuthKeyInvalid, AccessTokenInvalid, FloodWait, ApiIdInvalid
)
from telethon import TelegramClient
from telethon.sessions import StringSession
from telethon.errors import (
    AuthKeyUnregisteredError, UserDeactivatedError, SessionRevokedError,
    AuthKeyInvalidError, AccessTokenInvalidError, FloodWaitError
)
from .. import config

DC_LOCATIONS = {
    1: "Miami, USA",
    2: "Amsterdam, NL",
    3: "Miami, USA",
    4: "Amsterdam, NL",
    5: "Singapore",
}

async def _get_pyrogram_dc_id(client: Client, me) -> int:
    try:
        if hasattr(client, "storage") and hasattr(client.storage, "dc_id"):
            val = client.storage.dc_id
            if callable(val):
                res = val()
                if asyncio.iscoroutine(res):
                    res = await res
                if isinstance(res, int) and res > 0:
                    return res
            elif isinstance(val, int) and val > 0:
                return val
    except Exception:
        pass

    try:
        val = getattr(me, "dc_id", 0)
        if isinstance(val, int) and val > 0:
            return val
    except Exception:
        pass

    return 0

def _get_telethon_dc_id(t_client: TelegramClient, me) -> int:
    try:
        if hasattr(t_client, "session") and hasattr(t_client.session, "dc_id"):
            val = t_client.session.dc_id
            if isinstance(val, int) and val > 0:
                return val
    except Exception:
        pass
    try:
        val = getattr(me, "dc_id", 0)
        if isinstance(val, int) and val > 0:
            return val
    except Exception:
        pass
    return 0

async def check_pyrogram_spambot(client: Client, is_bot: bool) -> str:
    """Queries @SpamBot to check if the user account is restricted or spamblocked."""
    if is_bot:
        return "ℹ️ N/A (Bot Account)"
    try:
        me = await client.get_me()
        if getattr(me, "is_restricted", False):
            restrictions = getattr(me, "restriction_reason", [])
            reasons = ", ".join([getattr(r, "text", str(r)) for r in restrictions]) if restrictions else "Account is restricted"
            return f"🔴 Restricted ({reasons})"

        # Query @SpamBot
        await client.send_message("SpamBot", "/start")
        for _ in range(6):
            await asyncio.sleep(0.5)
            async for msg in client.get_chat_history("SpamBot", limit=1):
                if msg.from_user and msg.from_user.is_bot and (msg.text or msg.caption):
                    txt = (msg.text or msg.caption or "").lower()
                    if "good news" in txt or "no limits" in txt or "free as a bird" in txt:
                        return "🟢 Clean (No limits applied)"
                    elif "unfortunately" in txt or "limit" in txt or "restricted" in txt or "spam" in txt:
                        return "🔴 Restricted (Limitations applied by Telegram)"
        return "🟢 Clean (No limits applied)"
    except Exception:
        return "🟢 Clean (No limits applied)"

async def check_telethon_spambot(client: TelegramClient, is_bot: bool) -> str:
    """Queries @SpamBot in Telethon to check if user account is restricted."""
    if is_bot:
        return "ℹ️ N/A (Bot Account)"
    try:
        me = await client.get_me()
        if getattr(me, "restricted", False):
            restrictions = getattr(me, "restriction_reason", [])
            reasons = ", ".join([getattr(r, "text", str(r)) for r in restrictions]) if restrictions else "Account is restricted"
            return f"🔴 Restricted ({reasons})"

        # Query @SpamBot
        await client.send_message("SpamBot", "/start")
        for _ in range(6):
            await asyncio.sleep(0.5)
            messages = await client.get_messages("SpamBot", limit=1)
            if messages and len(messages) > 0:
                msg = messages[0]
                if not msg.out and (msg.text or msg.raw_text):
                    txt = (msg.text or msg.raw_text or "").lower()
                    if "good news" in txt or "no limits" in txt or "free as a bird" in txt:
                        return "🟢 Clean (No limits applied)"
                    elif "unfortunately" in txt or "limit" in txt or "restricted" in txt or "spam" in txt:
                        return "🔴 Restricted (Limitations applied by Telegram)"
        return "🟢 Clean (No limits applied)"
    except Exception:
        return "🟢 Clean (No limits applied)"

async def scan_pyrogram_dialogs(client: Client, is_bot: bool) -> dict:
    """Scans top 100 dialogs for channel and group ownership/admin privileges in Pyrogram."""
    if is_bot:
        return {
            "total_dialogs": 0,
            "owned_count": 0,
            "owned_titles": [],
            "admin_count": 0,
            "admin_titles": []
        }
    try:
        total = 0
        owned = []
        admin = []
        async for dialog in client.get_dialogs(limit=100):
            total += 1
            chat = dialog.chat
            if chat.type in (ChatType.CHANNEL, ChatType.SUPERGROUP, ChatType.GROUP):
                title = chat.title or "Untitled"
                if chat.username:
                    title += f" (@{chat.username})"

                # In Pyrogram, is_creator is available on chat model
                if getattr(chat, "is_creator", False):
                    owned.append(title)
                elif getattr(chat, "admin_rights", None) or getattr(chat, "can_manage_topics", None):
                    admin.append(title)

        return {
            "total_dialogs": total,
            "owned_count": len(owned),
            "owned_titles": owned[:5],
            "admin_count": len(admin),
            "admin_titles": admin[:5]
        }
    except Exception:
        return {
            "total_dialogs": 0,
            "owned_count": 0,
            "owned_titles": [],
            "admin_count": 0,
            "admin_titles": []
        }

async def scan_telethon_dialogs(client: TelegramClient, is_bot: bool) -> dict:
    """Scans top 100 dialogs for channel and group ownership/admin privileges in Telethon."""
    if is_bot:
        return {
            "total_dialogs": 0,
            "owned_count": 0,
            "owned_titles": [],
            "admin_count": 0,
            "admin_titles": []
        }
    try:
        total = 0
        owned = []
        admin = []
        async for dialog in client.iter_dialogs(limit=100):
            total += 1
            if dialog.is_channel or dialog.is_group:
                entity = dialog.entity
                title = dialog.name or "Untitled"
                username = getattr(entity, "username", None)
                if username:
                    title += f" (@{username})"

                if getattr(entity, "creator", False):
                    owned.append(title)
                elif getattr(entity, "admin_rights", None) is not None:
                    admin.append(title)

        return {
            "total_dialogs": total,
            "owned_count": len(owned),
            "owned_titles": owned[:5],
            "admin_count": len(admin),
            "admin_titles": admin[:5]
        }
    except Exception:
        return {
            "total_dialogs": 0,
            "owned_count": 0,
            "owned_titles": [],
            "admin_count": 0,
            "admin_titles": []
        }

async def inspect_session(session_string: str) -> dict:
    """
    Validates and inspects an existing Pyrogram v2 or Telethon session string in-memory.
    Checks account status, DC, Premium, SpamBlock, and Admin/Ownership footprint.
    Returns a dict with details or failure reason.
    """
    session_string = session_string.strip()
    if len(session_string) < 20:
        return {"valid": False, "reason": "Session string is too short or malformed"}

    api_id = config.API_ID
    api_hash = config.API_HASH

    # 1. Try Pyrogram v2
    pyro_err = None
    try:
        client = Client(
            name="check_pyro",
            api_id=api_id,
            api_hash=api_hash,
            session_string=session_string,
            in_memory=True,
            no_updates=True
        )
        await client.connect()
        try:
            me = await client.get_me()
            dc_id = await _get_pyrogram_dc_id(client, me)
            dc_name = DC_LOCATIONS.get(dc_id, "Unknown DC")
            acc_type = "🤖 Bot Account" if me.is_bot else "👤 User Account"
            spambot_status = await check_pyrogram_spambot(client, me.is_bot)
            footprint = await scan_pyrogram_dialogs(client, me.is_bot)

            return {
                "valid": True,
                "lib": "Pyrogram v2",
                "user_id": me.id,
                "name": f"{me.first_name or ''} {me.last_name or ''}".strip() or "Unknown",
                "username": f"@{me.username}" if me.username else "None",
                "acc_type": acc_type,
                "is_bot": me.is_bot,
                "is_premium": "✨ Yes" if getattr(me, "is_premium", False) else "No",
                "spambot_status": spambot_status,
                "dc_id": dc_id or 0,
                "dc_location": dc_name,
                "footprint": footprint
            }
        finally:
            if client.is_connected:
                await client.disconnect()
    except (AuthKeyUnregistered, SessionRevoked, UserDeactivated):
        return {"valid": False, "reason": "Session has been revoked or account is deactivated"}
    except AccessTokenInvalid:
        return {"valid": False, "reason": "Bot token session is invalid or has been regenerated in @BotFather"}
    except FloodWait as e:
        return {"valid": False, "reason": f"Telegram FloodWait: retry in {e.value}s"}
    except Exception as e:
        pyro_err = str(e)

    # 2. Try Telethon
    try:
        t_client = TelegramClient(
            StringSession(session_string),
            api_id,
            api_hash
        )
        await t_client.connect()
        try:
            if not await t_client.is_user_authorized():
                return {"valid": False, "reason": "Session is not authorized or has been terminated"}
            me = await t_client.get_me()
            dc_id = _get_telethon_dc_id(t_client, me)
            dc_name = DC_LOCATIONS.get(dc_id, "Unknown DC")
            is_bot = getattr(me, "bot", False)
            acc_type = "🤖 Bot Account" if is_bot else "👤 User Account"
            is_prem = getattr(me, "premium", False)
            spambot_status = await check_telethon_spambot(t_client, is_bot)
            footprint = await scan_telethon_dialogs(t_client, is_bot)

            return {
                "valid": True,
                "lib": "Telethon",
                "user_id": me.id,
                "name": f"{me.first_name or ''} {me.last_name or ''}".strip() or "Unknown",
                "username": f"@{me.username}" if me.username else "None",
                "acc_type": acc_type,
                "is_bot": is_bot,
                "is_premium": "✨ Yes" if is_prem else "No",
                "spambot_status": spambot_status,
                "dc_id": dc_id or 0,
                "dc_location": dc_name,
                "footprint": footprint
            }
        finally:
            if t_client.is_connected():
                await t_client.disconnect()
    except (AuthKeyUnregisteredError, SessionRevokedError, UserDeactivatedError):
        return {"valid": False, "reason": "Session has been revoked or account is deactivated"}
    except AccessTokenInvalidError:
        return {"valid": False, "reason": "Bot token session is invalid or regenerated"}
    except FloodWaitError as e:
        return {"valid": False, "reason": f"Telegram FloodWait: retry in {e.seconds}s"}
    except Exception as e:
        return {
            "valid": False,
            "reason": "Invalid session string format or unrecognized structure"
        }
