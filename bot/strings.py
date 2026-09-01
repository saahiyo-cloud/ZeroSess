from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton

# ---------- Texts ----------

START_TEXT = """{greet} {name} 👋

**⚡ ZeroSess** — Session Generator
Secure • Fast • Zero Logs

Generate **Pyrogram v2** & **Telethon** strings securely in seconds.

⚠️ __Never share your session string with anyone.__
"""

HELP_TEXT = """📖 **Quick Guide**

1️⃣ **Choose Library:** Pyrogram v2 or Telethon
2️⃣ **API Details:** Use default or your own from my.telegram.org
3️⃣ **Login:** Phone → OTP (with spaces: `1 2 3 4 5`)
4️⃣ **Receive:** Saved Messages + ephemeral copy

**Commands:**
• /start — Main menu
• /generate — Generate session
• /check — Inspect session
• /cancel — Abort wizard
• /ping — Latency & Uptime
"""

ABOUT_TEXT = """**⚡ ZeroSess**

Open-source Telegram session generator.

• **Libraries:** Pyrogram v2 & Telethon
• **Security:** 100% In-Memory • Auto-Purge
• **Zero Logs:** No PII or session storage

💬 Support: {support}
"""

CANCEL_TEXT = "❌ Cancelled. Send /start to begin again."

TIMEOUT_TEXT = "⏰ Timeout ({sec}s). Send /start to try again."

RATE_LIMIT_TEXT = "🚦 Rate limit exceeded. Try again in {mins}m. ({count}/{limit} limit)"

MUST_JOIN_TEXT = "🔒 Please join {channel} to use this bot, then tap **Try Again**."

# ---------- Keyboards ----------

def kb_start():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🚀 Generate", callback_data="menu:generate"),
         InlineKeyboardButton("🔍 Check", callback_data="menu:check")],
        [InlineKeyboardButton("📖 Help", callback_data="menu:help"),
         InlineKeyboardButton("ℹ️ About", callback_data="menu:about")],
        [InlineKeyboardButton("📊 Ping", callback_data="menu:ping"),
         InlineKeyboardButton("🔗 API Tools", url="https://my.telegram.org")],
    ])

def kb_choose_lib():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("👤 Pyrogram (User)", callback_data="gen:user:pyro"),
         InlineKeyboardButton("👤 Telethon (User)", callback_data="gen:user:tele")],
        [InlineKeyboardButton("🤖 Pyrogram (Bot)", callback_data="gen:bot:pyro"),
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
        [InlineKeyboardButton("⚡ Use Default API", callback_data="gen:default_api")],
        [InlineKeyboardButton("❌ Cancel", callback_data="menu:cancel")]
    ])

def kb_got_it():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("✅ Continue", callback_data="gen:continue")],
        [InlineKeyboardButton("❌ Cancel", callback_data="menu:cancel")]
    ])

def kb_after_gen():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🗑️ Delete Now", callback_data="gen:burn")],
        [InlineKeyboardButton("🔄 Generate Again", callback_data="menu:generate")],
    ])

def kb_after_check():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🗑️ Delete Now", callback_data="gen:burn")],
        [InlineKeyboardButton("🔍 Check Another", callback_data="menu:check"),
         InlineKeyboardButton("🚀 Generate", callback_data="menu:generate")],
    ])

def kb_must_join(channel: str):
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
        [InlineKeyboardButton("🔗 API Tools", url="https://my.telegram.org")],
        [InlineKeyboardButton("⬅️ Back", callback_data="menu:start")],
    ])

# ---------- Step prompts ----------

STEP_API_ID = """📋 **Step 1/5 — API ID**

Send your **API_ID** from https://my.telegram.org
Or tap **⚡ Use Default API** below to skip.
"""

STEP_API_HASH = """🔑 **Step 2/5 — API HASH**

Send your **API_HASH** (32 hex characters):
"""

STEP_API_ID_BOT = """📋 **Step 1/3 — API ID**

Send your **API_ID** from https://my.telegram.org
Or tap **⚡ Use Default API** below to skip.
"""

STEP_API_HASH_BOT = """🔑 **Step 2/3 — API HASH**

Send your **API_HASH** (32 hex characters):
"""

STEP_BOT_TOKEN = """🤖 **Step 3/3 — Bot Token**

Send your **BOT_TOKEN** from @BotFather:
"""

STEP_PHONE = """📱 **Step 3/5 — Phone Number**

Send your phone with country code (e.g. `+919876543210`):
"""

STEP_OTP = """📩 **Step 4/5 — OTP Code**

Enter the code sent by Telegram.

⚠️ **Format:** Put spaces between digits (e.g. `1 2 3 4 5`)
"""

STEP_2FA = """🔐 **Step 5/5 — 2FA Password**

Your account has 2FA enabled. Send your **password**:
"""

GENERATING_TEXT = "⏳ **Generating session…**"

SUCCESS_CAPTION = """✅ **Session Generated — {lib}**

`{session}`

📨 Sent to **Saved Messages**.
__Auto-deletes in {sec}s.__
"""

SUCCESS_CAPTION_BOT = """✅ **Bot Session Generated — {lib}**

`{session}`

__Auto-deletes in {sec}s.__
"""

CHECK_PROMPT = """🔍 **Session String Inspector**

Send any **Pyrogram v2** or **Telethon** session string to inspect.

__Your input message is deleted instantly.__
"""

CHECK_ACTIVE_TEXT = """✅ **Session Valid & Active**

• **Library:** `{lib}` ({acc_type})
• **Account:** {name} (`{user_id}`)
• **Username:** {username}
• **SpamBot:** {spambot}
• **DC:** `DC {dc_id}` ({dc_location}) | **Premium:** {is_premium}

📊 **Footprint:** `{total_dialogs}` chats | `{owned_count}` owned | `{admin_count}` admin

__Auto-deletes in {sec}s.__
"""

CHECK_INVALID_TEXT = """❌ **Session Invalid / Revoked**

• **Reason:** {reason}
• Send /generate to create a new session.
"""
