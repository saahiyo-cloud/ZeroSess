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
                        first_line = (msg.text or "").split("\n")[0][:50]
                        return f"🔴 Restricted ({first_line})"
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
                        first_line = (msg.text or "").split("\n")[0][:50]
                        return f"🔴 Restricted ({first_line})"
        return "🟢 Clean (No limits applied)"
    except Exception:
        return "🟢 Clean (No limits applied)"

async def inspect_session(session_string: str) -> dict:
    """
    Validates and inspects an existing Pyrogram v2 or Telethon session string in-memory.
    Checks account status, DC, Premium, and SpamBlock status.
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
            spambot_status = await check_pyrogram_spambot(client, me.is_bot)

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
            spambot_status = await check_telethon_spambot(t_client, is_bot)

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
            "reason": "Invalid session string format or unrecognized structure"
        }
