import io
import time
import base64
import asyncio
import logging
import qrcode
from pyrogram import Client, raw
from pyrogram.errors import SessionPasswordNeeded, FloodWait
from telethon import TelegramClient
from telethon.errors import SessionPasswordNeededError, FloodWaitError

logger = logging.getLogger("session-gen.qr")

class QRError(Exception):
    def __init__(self, user_msg: str):
        super().__init__(user_msg)
        self.user_msg = user_msg

def generate_qr_image(url: str) -> io.BytesIO:
    """Generates an in-memory PNG QR code image from a given URL."""
    qr = qrcode.QRCode(
        version=None,
        error_correction=qrcode.constants.ERROR_CORRECT_M,
        box_size=8,
        border=2,
    )
    qr.add_data(url)
    qr.make(fit=True)
    img = qr.make_image(fill_color="black", back_color="white")
    buf = io.BytesIO()
    buf.name = "login_qr.png"
    img.save(buf, format="PNG")
    buf.seek(0)
    return buf

async def export_pyrogram_qr(client: Client, api_id: int, api_hash: str) -> tuple[str, int]:
    """
    Exports a Pyrogram QR login token.
    Returns (tg_login_url, expires_at_timestamp).
    """
    try:
        token_res = await client.invoke(
            raw.functions.auth.ExportLoginToken(
                api_id=api_id,
                api_hash=api_hash,
                except_ids=[]
            )
        )
        if isinstance(token_res, raw.types.auth.LoginToken):
            b64 = base64.urlsafe_b64encode(token_res.token).decode("utf-8").rstrip("=")
            url = f"tg://login?token={b64}"
            return url, token_res.expires
        elif isinstance(token_res, raw.types.auth.LoginTokenSuccess):
            return "", 0
        else:
            raise QRError("❌ Could not export QR login token.")
    except FloodWait as e:
        raise QRError(f"🚦 FloodWait: retry in {e.value}s.")
    except Exception as e:
        raise QRError(f"❌ QR export failed: `{e}`")

async def check_pyrogram_qr(client: Client, api_id: int, api_hash: str) -> bool:
    """
    Polls token status in Pyrogram.
    Returns True if login succeeded, False if still waiting.
    Raises SessionPasswordNeeded if 2FA password is required.
    """
    try:
        token_res = await client.invoke(
            raw.functions.auth.ExportLoginToken(
                api_id=api_id,
                api_hash=api_hash,
                except_ids=[]
            )
        )
        if isinstance(token_res, raw.types.auth.LoginTokenSuccess):
            return True
        return False
    except SessionPasswordNeeded:
        raise
    except FloodWait as e:
        raise QRError(f"🚦 FloodWait: retry in {e.value}s.")
    except Exception as e:
        logger.debug(f"QR poll error: {e}")
        return False
