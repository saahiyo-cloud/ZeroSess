import os
import re
from dotenv import load_dotenv

load_dotenv()

def _req(name: str) -> str:
    v = os.getenv(name, "").strip()
    if not v:
        raise RuntimeError(f"Missing required env var: {name} — set it in .env or environment")
    return v

def _opt(name: str, default: str = "") -> str:
    return os.getenv(name, default).strip()

# --- Required ---
API_ID: int = int(_req("API_ID")) if os.getenv("API_ID") else 0
API_HASH: str = _req("API_HASH") if os.getenv("API_HASH") else ""
BOT_TOKEN: str = _req("BOT_TOKEN") if os.getenv("BOT_TOKEN") else ""

# Allow missing at import for lint; validate at runtime
def validate_or_raise():
    api_id_raw = os.getenv("API_ID", "").strip()
    api_hash_raw = os.getenv("API_HASH", "").strip()
    bot_token_raw = os.getenv("BOT_TOKEN", "").strip()
    if not api_id_raw or not api_hash_raw or not bot_token_raw:
        raise RuntimeError(
            "API_ID / API_HASH / BOT_TOKEN missing.\n"
            "Copy .env.example -> .env and fill values.\n"
            "Get API_ID/HASH: https://my.telegram.org -> API development tools\n"
            "Get BOT_TOKEN: https://t.me/BotFather -> /newbot"
        )
    if not api_id_raw.isdigit():
        raise RuntimeError("API_ID must be numeric (e.g. 1234567)")
    if not re.fullmatch(r"[0-9a-fA-F]{32}", api_hash_raw):
        raise RuntimeError("API_HASH must be 32 hex chars")
    # bot token format 123:ABC
    if not re.fullmatch(r"\d+:[\w\-]+", bot_token_raw):
        raise RuntimeError("BOT_TOKEN looks invalid (expected 123456:ABC...)")

def _parse_int(name: str, default: int = 0) -> int:
    val = os.getenv(name, "").strip()
    if not val:
        return default
    try:
        return int(val)
    except ValueError:
        return default

def _parse_channel(name: str) -> int | str | None:
    val = os.getenv(name, "").strip()
    if not val or val == "0":
        return None
    if re.fullmatch(r"^-?\d+$", val):
        return int(val)
    clean = re.sub(r"^(https?://)?(www\.)?t\.me/", "", val).lstrip("@").strip()
    if clean and not clean.startswith("+"):
        return f"@{clean}"
    return val or None

# --- Optional ---
OWNER_ID: int = _parse_int("OWNER_ID", 0)
LOG_CHANNEL: int | str | None = _parse_channel("LOG_CHANNEL")  # accepts chat ID (-100...), @username, or t.me link
MUST_JOIN: str = _opt("MUST_JOIN", "")  # e.g. @yourchannel or https://t.me/...
SUPPORT_CHAT: str = _opt("SUPPORT_CHAT", "")
SESSION_TIMEOUT: int = _parse_int("SESSION_TIMEOUT", 300)  # seconds per step
RATE_LIMIT_COUNT: int = _parse_int("RATE_LIMIT_COUNT", 3)
RATE_LIMIT_WINDOW: int = _parse_int("RATE_LIMIT_WINDOW", 3600)  # seconds
AUTO_DELETE_SECONDS: int = _parse_int("AUTO_DELETE_SECONDS", 300)

# Messages that should never be logged
SENSITIVE_KEYS = {"phone", "otp", "password", "api_hash", "session_string"}
