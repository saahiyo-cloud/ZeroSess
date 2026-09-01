import re
import asyncio
from pyrogram import Client
from pyrogram.errors import (
    ApiIdInvalid, ApiIdPublishedFlood, AccessTokenInvalid,
    PhoneNumberInvalid, PhoneNumberBanned, PhoneNumberFlood,
    PhoneCodeInvalid, PhoneCodeExpired,
    SessionPasswordNeeded, PasswordHashInvalid, FloodWait
)

PHONE_RE = re.compile(r"^\+[0-9]{7,15}$")
API_HASH_RE = re.compile(r"^[0-9a-fA-F]{32}$")

class GenError(Exception):
    def __init__(self, user_msg: str):
        super().__init__(user_msg)
        self.user_msg = user_msg

def validate_api_id(text: str) -> int:
    t = text.strip()
    if not t.isdigit() or not (5 <= len(t) <= 10):
        raise GenError("❌ `API_ID` must be 5–10 digits. Example: `1234567`\nGet it: https://my.telegram.org → API development tools")
    return int(t)

def validate_api_hash(text: str) -> str:
    t = text.strip()
    if not API_HASH_RE.fullmatch(t):
        raise GenError("❌ `API_HASH` must be exactly 32 hex characters (0-9, a-f).\nFound next to API_ID on my.telegram.org")
    return t.lower()

def validate_phone(text: str) -> str:
    t = text.strip().replace(" ", "").replace("-", "")
    if not PHONE_RE.fullmatch(t):
        raise GenError("❌ Invalid phone. Use international format: `+919876543210`\nInclude `+` and country code.")
    return t

def normalize_otp(text: str) -> str:
    # accepts "1 2 3 4 5" / "1-2-3-4-5" / "12345"
    t = re.sub(r"[^0-9]", "", text.strip())
    if not (4 <= len(t) <= 6) or not t.isdigit():
        raise GenError("❌ OTP must be 4–6 digits. Example: `12345` or `1 2 3 4 5`")
    return t

async def generate_pyrogram_string(
    api_id: int,
    api_hash: str,
    phone: str,
    otp: str,
    password: str | None = None,
    *,
    phone_code_hash: str | None = None,
) -> tuple[str, str]:
    """
    Returns (session_string, phone_code_hash_or_used)
    If phone_code_hash is None, this function does send_code + sign_in.
    If phone_code_hash provided, only sign_in (used to separate steps for wizard).
    For wizard we expose two-phase helpers below.
    """
    raise NotImplementedError("Use start_client/send_code/sign_in helpers")

# Wizard-friendly helpers — keep client lifecycle explicit so caller can handle 2FA branching

async def create_client(api_id: int, api_hash: str) -> Client:
    c = Client(name="gen_pyro", api_id=api_id, api_hash=api_hash, in_memory=True)
    try:
        await c.connect()
    except ApiIdInvalid:
        raise GenError("❌ Invalid `API_ID` / `API_HASH` combination. Double-check at https://my.telegram.org")
    except ApiIdPublishedFlood:
        raise GenError("❌ This API_ID is flood-limited. Use your own API credentials from my.telegram.org")
    except FloodWait as e:
        raise GenError(f"🚦 FloodWait: retry in {e.value}s. Telegram is rate-limiting this IP.")
    except Exception as e:
        raise GenError(f"❌ Connect failed: `{e}`")
    return c

async def send_code(client: Client, phone: str) -> str:
    try:
        sent = await client.send_code(phone)
        return sent.phone_code_hash
    except PhoneNumberInvalid:
        raise GenError("❌ Invalid phone number. Check country code and digits.")
    except PhoneNumberBanned:
        raise GenError("❌ This phone number is banned from Telegram.")
    except PhoneNumberFlood:
        raise GenError("❌ This phone triggered flood protection. Try later.")
    except ApiIdInvalid:
        raise GenError("❌ Invalid API_ID/API_HASH. Re-check my.telegram.org")
    except FloodWait as e:
        raise GenError(f"🚦 FloodWait: retry in {e.value}s.")
    except Exception as e:
        raise GenError(f"❌ Could not send OTP: `{e}`")

async def sign_in(client: Client, phone: str, phone_code_hash: str, otp: str) -> bool:
    """Returns True if fully signed in, False if 2FA needed (raises SessionPasswordNeeded)."""
    try:
        await client.sign_in(phone, phone_code_hash, otp)
        return True
    except PhoneCodeInvalid:
        raise GenError("❌ Wrong OTP. Check Telegram → Login Codes and retry.")
    except PhoneCodeExpired:
        raise GenError("❌ OTP expired. Restart with /generate to get a new code.")
    except SessionPasswordNeeded:
        # signal caller to ask password
        raise
    except PasswordHashInvalid:
        raise GenError("❌ Wrong 2FA password.")
    except FloodWait as e:
        raise GenError(f"🚦 FloodWait: retry in {e.value}s.")
    except Exception as e:
        raise GenError(f"❌ Sign-in failed: `{e}`")

async def check_password(client: Client, password: str):
    try:
        await client.check_password(password)
    except PasswordHashInvalid:
        raise GenError("❌ Wrong 2FA password. Try again.")
    except FloodWait as e:
        raise GenError(f"🚦 FloodWait: retry in {e.value}s.")
    except Exception as e:
        raise GenError(f"❌ Password check failed: `{e}`")

async def export_string(client: Client) -> str:
    try:
        s = await client.export_session_string()
        if not s or len(s) < 20:
            raise GenError("❌ Exported string looks empty — try again.")
        return s
    except Exception as e:
        raise GenError(f"❌ Could not export session: `{e}`")

async def send_to_saved(client: Client, text: str):
    try:
        await client.send_message("me", text)
    except Exception:
        pass  # not fatal

async def safe_disconnect(client: Client):
    try:
        if client.is_connected:
            await client.disconnect()
    except Exception:
        pass
