from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton

# ---------- Texts ----------

START_TEXT = """{greet} {name} 👋

**⚡ ZeroSess — Session String Generator**
Secure • Fast • Zero Logs • Auto-Burn

Generate **Pyrogram v2** or **Telethon** session strings for your userbot or bot securely.

⚠️ __Your session string equals account access. Never share it with untrusted parties.__
"""

HELP_TEXT = """**📖 How to generate — 4 simple steps**

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
/generate — generate string (User or Bot)
/check — validate & inspect existing session string
/cancel — cancel current flow
/ping — latency
/help — this guide
/about — about ZeroSess
/destroy — session revocation guide

💡 Tip: Use `/cancel` anytime to abort. Sensitive messages are auto-deleted.
"""

ABOUT_TEXT = """**⚡ ZeroSess**

Production-grade Telegram session generator.

• **Pyrogram v2** & **Telethon** support
• In-memory only — no `.session` files on disk
• Auto-delete OTP / password / phone
• FloodWait & 2FA handling
• Rate-limited • Zero PII logging

Built with Pyrogram + Telethon + tgcrypto.
Open-source on GitHub — deploy your own instance.

Support: {support}
"""

CANCEL_TEXT = "❌ Cancelled. Send /start to begin again. Sensitive messages deleted where possible."

TIMEOUT_TEXT = "⏰ Timeout — no reply in {sec}s. Send /start to try again."

RATE_LIMIT_TEXT = "🚦 Too many attempts. Try again after {mins} min. ({count}/{limit} in last hour)"

MUST_JOIN_TEXT = "🔒 Please join {channel} to use this bot, then tap **Try Again**."

# ---------- Keyboards ----------

def kb_start():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🚀 Generate Session", callback_data="menu:generate"),
         InlineKeyboardButton("🔍 Check Session", callback_data="menu:check")],
        [InlineKeyboardButton("📖 Help & Guide", callback_data="menu:help"),
         InlineKeyboardButton("ℹ️ About", callback_data="menu:about")],
        [InlineKeyboardButton("📊 Ping", callback_data="menu:ping"),
         InlineKeyboardButton("🔗 my.telegram.org", url="https://my.telegram.org")],
    ])

def kb_choose_lib():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("👤 Pyrogram v2 (User)", callback_data="gen:user:pyro"),
         InlineKeyboardButton("👤 Telethon (User)", callback_data="gen:user:tele")],
        [InlineKeyboardButton("🤖 Pyrogram v2 (Bot)", callback_data="gen:bot:pyro"),
         InlineKeyboardButton("🤖 Telethon (Bot)", callback_data="gen:bot:tele")],
        [InlineKeyboardButton("⬅️ Back", callback_data="menu:start"),
         InlineKeyboardButton("❌ Cancel", callback_data="menu:cancel")],
    ])

def kb_cancel_only():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("❌ Cancel", callback_data="menu:cancel")]
    ])

def kb_step_api_id():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("⚡ Use Default (Skip API ID/Hash)", callback_data="gen:default_api")],
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

def kb_after_check():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🗑️ Delete This Message", callback_data="gen:burn")],
        [InlineKeyboardButton("🔍 Check Another", callback_data="menu:check"),
         InlineKeyboardButton("🚀 Generate", callback_data="menu:generate")],
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

Send your custom **API_ID** from https://my.telegram.org, or tap **⚡ Use Default** below to skip.

• Example: `1234567` (5-10 digits)
• Or tap **⚡ Use Default** to proceed immediately

Type `/cancel` to abort.
"""

STEP_API_HASH = """**Step 2/5 — API_HASH** 🔑

Send your **API_HASH** (32 hex characters)

• Example: `abc123def456...` (32 chars)
• Found next to API_ID on my.telegram.org

Type `/cancel` to abort.
"""

STEP_API_ID_BOT = """**Step 1/3 — API_ID** 📋

Send your custom **API_ID** from https://my.telegram.org, or tap **⚡ Use Default** below to skip.

• Example: `1234567` (5-10 digits)
• Or tap **⚡ Use Default** to proceed immediately

Type `/cancel` to abort.
"""

STEP_API_HASH_BOT = """**Step 2/3 — API_HASH** 🔑

Send your **API_HASH** (32 hex characters)

• Example: `abc123def456...` (32 chars)
• Found next to API_ID on my.telegram.org

Type `/cancel` to abort.
"""

STEP_BOT_TOKEN = """**Step 3/3 — Bot Token** 🤖

Send your **BOT_TOKEN** from https://t.me/BotFather

• Example: `123456789:ABCdefGhIJKlmNoPQRsTUVwxyZ12345`
• Created via `/newbot` or `/token` on @BotFather

⚠️ Token message will be deleted instantly after use and never logged.

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

__Tap to copy. This message auto-deletes in {sec}s → tap 🗑️ to delete now.__
"""

SUCCESS_CAPTION_BOT = """✅ **Bot Token Session Generated — {lib}**

⚠️ **SECURITY WARNING**
• This session string grants MTProto API access as your bot
• Keep it secret and never commit to public repositories

`{session}`

__Tap to copy. This message auto-deletes in {sec}s → tap 🗑️ to delete now.__
"""

CHECK_PROMPT = """**🔍 Session String Validator & Inspector**

Send any **Pyrogram v2** or **Telethon** session string to inspect its status.

• Verifies if the session is currently active, expired, or revoked
• Identifies account type (User / Bot), User ID, Name, Username
• Checks @SpamBot restriction & limitation status
• Checks connected Data Center (DC) and Premium status
• 100% In-memory inspection — no credentials stored or logged

⚠️ **Security:** Your input message containing the string will be **immediately purged**.

Type `/cancel` to abort.
"""

CHECK_ACTIVE_TEXT = """✅ **Session String Valid & Active**

• **Library Format:** `{lib}`
• **Account Type:** {acc_type}
• **Name:** {name}
• **Telegram ID:** `{user_id}`
• **Username:** {username}
• **SpamBlock Status:** {spambot}
• **Data Center:** `DC {dc_id}` ({dc_location})
• **Telegram Premium:** {is_premium}

📊 **Channel & Group Footprint:**
• **Dialogs Scanned:** `{total_dialogs}`
• **👑 Owned Channels/Groups:** `{owned_count}`{owned_list}
• **🛡️ Admin in Channels/Groups:** `{admin_count}`{admin_list}

__This inspection report will auto-delete in {sec}s for security.__
"""

CHECK_INVALID_TEXT = """❌ **Session String Invalid / Revoked**

• **Status:** {reason}
• **Resolution:** Generate a fresh session using /generate or restart your app.
"""
