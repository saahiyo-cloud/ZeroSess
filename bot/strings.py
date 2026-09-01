from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton

# ---------- Texts ----------

START_TEXT = """{greet} {name} 👋

**🔑 Session String Generator**
Secure • Fast • No logs • Auto-burn

Generate **Pyrogram** or **Telethon** string for your userbot / bot.

⚠️ *Your session = your account password. Never share it.*
"""

HELP_TEXT = """**📖 How to generate — 4 steps**

**Step 1 — Get API credentials**
1. Open https://my.telegram.org → Log in
2. Go to **API development tools**
3. Create app (any name) → copy `API_ID` & `API_HASH`

**Step 2 — Choose library**
Tap **Pyrogram** or **Telethon** below.

**Step 3 — Provide details**
Bot will ask:
• `API_ID` (e.g. `1234567`)
• `API_HASH` (32 hex chars)
• `Phone` with country code (`+919876543210`)
• `OTP` — Telegram sends to your account (format `1 2 3 4 5` also works)
• `2FA Password` — only if you enabled it

**Step 4 — Get string**
String is sent to your **Saved Messages** + one-time copy here (auto-deletes in 5 min).

**Commands**
/start — start wizard
/generate — generate string
/cancel — cancel current flow
/ping — latency
/help — this guide
/about — about bot

💡 Tip: Use `/cancel` anytime to abort. Sensitive messages are auto-deleted.
"""

ABOUT_TEXT = """**🔐 Session Gen Bot**

Production-grade Telegram session generator.

• **Pyrogram v2** & **Telethon** support
• In-memory only — no `.session` files
• Auto-delete OTP / password / phone
• FloodWait & 2FA handling
• Rate-limited • No PII logging

Built with Pyrogram + Telethon + tgcrypto
Open-source — deploy your own instance.

Support: {support}
"""

CANCEL_TEXT = "❌ Cancelled. Send /start to begin again. Sensitive messages deleted where possible."

TIMEOUT_TEXT = "⏰ Timeout — no reply in {sec}s. Send /start to try again."

RATE_LIMIT_TEXT = "🚦 Too many attempts. Try again after {mins} min. ({count}/{limit} in last hour)"

MUST_JOIN_TEXT = "🔒 Please join {channel} to use this bot, then tap **Try Again**."

# ---------- Keyboards ----------

def kb_start():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🚀 Generate Session", callback_data="menu:generate")],
        [InlineKeyboardButton("📖 Help & Guide", callback_data="menu:help"),
         InlineKeyboardButton("ℹ️ About", callback_data="menu:about")],
        [InlineKeyboardButton("📊 Ping", callback_data="menu:ping"),
         InlineKeyboardButton("🔗 my.telegram.org", url="https://my.telegram.org")],
    ])

def kb_choose_lib():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🔥 Pyrogram v2", callback_data="gen:pyro")],
        [InlineKeyboardButton("⚡ Telethon", callback_data="gen:tele")],
        [InlineKeyboardButton("⬅️ Back", callback_data="menu:start"),
         InlineKeyboardButton("❌ Cancel", callback_data="menu:cancel")],
    ])

def kb_cancel_only():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("❌ Cancel", callback_data="menu:cancel")]
    ])

def kb_got_it():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("✅ I Understand — Continue", callback_data="gen:continue")],
        [InlineKeyboardButton("❌ Cancel", callback_data="menu:cancel")]
    ])

def kb_after_gen():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🗑️ Delete This Message", callback_data="gen:burn")],
        [InlineKeyboardButton("🔄 Generate Another", callback_data="menu:generate")],
    ])

def kb_must_join(channel: str):
    # channel may be @name or https://t.me/...
    if channel.startswith("http"):
        url = channel
    elif channel.startswith("@"):
        url = f"https://t.me/{channel.lstrip('@')}"
    else:
        url = f"https://t.me/{channel}"
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("📢 Join Channel", url=url)],
        [InlineKeyboardButton("🔄 Try Again", callback_data="menu:start")],
    ])

def kb_help_actions():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🚀 Generate Now", callback_data="menu:generate")],
        [InlineKeyboardButton("🔗 Get API_ID/HASH", url="https://my.telegram.org")],
        [InlineKeyboardButton("⬅️ Back", callback_data="menu:start")],
    ])

# ---------- Step prompts ----------

STEP_API_ID = """**Step 1/5 — API_ID** 📋

Send your **API_ID** from https://my.telegram.org

• Tap **API development tools**
• Example: `1234567`
• Only numbers, 5-8 digits

Type `/cancel` to abort.
"""

STEP_API_HASH = """**Step 2/5 — API_HASH** 🔑

Send your **API_HASH** (32 hex characters)

• Example: `abc123def456...` (32 chars)
• Found next to API_ID on my.telegram.org

Type `/cancel` to abort.
"""

STEP_PHONE = """**Step 3/5 — Phone Number** 📱

Send your Telegram **phone number with country code**

• Example: `+919876543210` or `+14155552671`
• Include `+` prefix

⚠️ Phone message will be deleted instantly after use.

Type `/cancel` to abort.
"""

STEP_OTP = """**Step 4/5 — OTP Code** 📩

Telegram sent a code to your account (and SMS if needed).

Send the **OTP** here:
• Accept `12345` or `1 2 3 4 5` or `1-2-3-4-5`

Code expires in ~5 minutes.

Type `/cancel` to abort.
"""

STEP_2FA = """**Step 5/5 — Two-Step Password** 🔐

Your account has 2FA enabled.

Send your **password** (not OTP):

⚠️ Password message will be deleted instantly and never logged.

Type `/cancel` to abort.
"""

GENERATING_TEXT = "⏳ **Generating session…** Please wait."

SUCCESS_CAPTION = """✅ **Session Generated — {lib}**

⚠️ **SECURITY WARNING**
• This string = your account password
• Never share / commit to GitHub
• Revoke via Telegram → Settings → Devices if leaked

📨 Also sent to your **Saved Messages** for safekeeping.

`{session}`

_Tap to copy. This message auto-deletes in {sec}s → tap 🗑️ to delete now._
"""
