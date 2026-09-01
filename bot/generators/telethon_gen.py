import re
from telethon import TelegramClient
from telethon.sessions import StringSession
from telethon.errors import (
    ApiIdInvalidError, ApiHashInvalidError,
    PhoneNumberInvalidError, PhoneNumberBannedError, PhoneNumberFloodError,
    PhoneCodeInvalidError, PhoneCodeExpiredError,
    SessionPasswordNeededError, PasswordHashInvalidError, FloodWaitError,
    AccessTokenInvalidError
)

BOT_TOKEN_RE = re.compile(r"^\d{5,15}:[A-Za-z0-9_-]{30,50}$")

class GenError(Exception):
    def __init__(self, user_msg: str):
        super().__init__(user_msg)
        self.user_msg = user_msg

def validate_bot_token(text: str) -> str:
    t = text.strip()
    if not BOT_TOKEN_RE.fullmatch(t):
        raise GenError("❌ Invalid `BOT_TOKEN` format. Example: `123456789:ABCdefGhIJKlmNoPQRsTUVwxyZ12345`\nGet it from @BotFather → /newbot")
    return t

async def create_client(api_id: int, api_hash: str) -> TelegramClient:
    c = TelegramClient(StringSession(), api_id, api_hash)
    try:
        await c.connect()
    except ApiIdInvalidError:
        raise GenError("❌ Invalid `API_ID` — check https://my.telegram.org")
    except ApiHashInvalidError:
        raise GenError("❌ Invalid `API_HASH` — 32 hex chars from my.telegram.org")
    except FloodWaitError as e:
        raise GenError(f"🚦 FloodWait: retry in {e.seconds}s.")
    except Exception as e:
        raise GenError(f"❌ Connect failed: `{e}`")
    return c

async def send_code(client: TelegramClient, phone: str):
    try:
        sent = await client.send_code_request(phone)
        return sent.phone_code_hash
    except PhoneNumberInvalidError:
        raise GenError("❌ Invalid phone number. Use `+<country><number>` like `+919876543210`")
    except PhoneNumberBannedError:
        raise GenError("❌ This phone is banned.")
    except PhoneNumberFloodError:
        raise GenError("❌ Phone flood — too many attempts. Try later.")
    except ApiIdInvalidError:
        raise GenError("❌ Invalid API_ID/API_HASH")
    except FloodWaitError as e:
        raise GenError(f"🚦 FloodWait: retry in {e.seconds}s.")
    except Exception as e:
        raise GenError(f"❌ Could not send OTP: `{e}`")

async def sign_in(client: TelegramClient, phone: str, phone_code_hash: str, otp: str):
    try:
        await client.sign_in(phone=phone, code=otp, phone_code_hash=phone_code_hash)
        return True
    except PhoneCodeInvalidError:
        raise GenError("❌ Wrong OTP. Check your Telegram login code.")
    except PhoneCodeExpiredError:
        raise GenError("❌ OTP expired. Restart with /generate")
    except SessionPasswordNeededError:
        raise
    except PasswordHashInvalidError:
        raise GenError("❌ Wrong 2FA password.")
    except FloodWaitError as e:
        raise GenError(f"🚦 FloodWait: retry in {e.seconds}s.")
    except Exception as e:
        raise GenError(f"❌ Sign-in failed: `{e}`")

async def sign_in_bot(client: TelegramClient, bot_token: str) -> bool:
    try:
        await client.sign_in(bot_token=bot_token)
        return True
    except (AccessTokenInvalidError, ApiIdInvalidError):
        raise GenError("❌ Invalid `BOT_TOKEN` or `API_ID`/`API_HASH`. Check @BotFather & my.telegram.org")
    except FloodWaitError as e:
        raise GenError(f"🚦 FloodWait: retry in {e.seconds}s.")
    except Exception as e:
        raise GenError(f"❌ Bot sign-in failed: `{e}`")

async def check_password(client: TelegramClient, password: str):
    try:
        await client.sign_in(password=password)
    except PasswordHashInvalidError:
        raise GenError("❌ Wrong 2FA password.")
    except FloodWaitError as e:
        raise GenError(f"🚦 FloodWait: retry in {e.seconds}s.")
    except Exception as e:
        raise GenError(f"❌ Password check failed: `{e}`")

def export_string(client: TelegramClient) -> str:
    try:
        s = client.session.save()
        if not s or len(s) < 20:
            raise GenError("❌ Exported Telethon string empty — retry.")
        return s
    except Exception as e:
        raise GenError(f"❌ Could not export Telethon string: `{e}`")

async def send_to_saved(client: TelegramClient, text: str):
    try:
        await client.send_message("me", text)
    except Exception:
        pass

async def safe_disconnect(client: TelegramClient):
    try:
        if client.is_connected():
            await client.disconnect()
    except Exception:
        pass
