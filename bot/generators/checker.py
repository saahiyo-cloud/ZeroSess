import asyncio
from pyrogram import Client
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

async def inspect_session(session_string: str) -> dict:
    """
    Validates and inspects an existing Pyrogram v2 or Telethon session string in-memory.
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
            dc_id = getattr(client.storage, "dc_id", 0) if hasattr(client, "storage") else (getattr(me, "dc_id", 0) or 0)
            dc_name = DC_LOCATIONS.get(dc_id, "Unknown DC")
            acc_type = "🤖 Bot Account" if me.is_bot else "👤 User Account"
            return {
                "valid": True,
                "lib": "Pyrogram v2",
                "user_id": me.id,
                "name": f"{me.first_name or ''} {me.last_name or ''}".strip() or "Unknown",
                "username": f"@{me.username}" if me.username else "None",
                "acc_type": acc_type,
                "is_bot": me.is_bot,
                "is_premium": "✨ Yes" if getattr(me, "is_premium", False) else "No",
                "dc_id": dc_id or 0,
                "dc_location": dc_name
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
            dc_id = getattr(t_client.session, "dc_id", 0) if hasattr(t_client, "session") else 0
            dc_name = DC_LOCATIONS.get(dc_id, "Unknown DC")
            is_bot = getattr(me, "bot", False)
            acc_type = "🤖 Bot Account" if is_bot else "👤 User Account"
            is_prem = getattr(me, "premium", False)
            return {
                "valid": True,
                "lib": "Telethon",
                "user_id": me.id,
                "name": f"{me.first_name or ''} {me.last_name or ''}".strip() or "Unknown",
                "username": f"@{me.username}" if me.username else "None",
                "acc_type": acc_type,
                "is_bot": is_bot,
                "is_premium": "✨ Yes" if is_prem else "No",
                "dc_id": dc_id or 0,
                "dc_location": dc_name
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
            "reason": f"Invalid session string format or unrecognized structure"
        }
