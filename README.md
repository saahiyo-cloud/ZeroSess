# ⚡ ZeroSess — Production Grade Session String Bot

Secure Telegram bot to generate **Pyrogram v2** & **Telethon** session strings with guided wizard UI, auto-burn, and zero PII logging.

> **Security:** In-memory only, no `.session` files, OTP/password/phone auto-deleted, rate-limited, FloodWait & 2FA handling. String sent to **Saved Messages** + one-time ephemeral copy.

## ✨ Features

- **Wizard UI:** Step 1/5 progress, `Cancel` on every step, `/cancel` anytime
- **Validation:** `API_ID` numeric, `API_HASH` 32 hex, `phone` `+<code><num>`, OTP `1 2 3 4 5` normalize
- **Error mapping:** `PhoneNumberInvalid`, `PhoneCodeExpired`, `SessionPasswordNeeded`, `FloodWait Xs`, etc. → user-friendly
- **Auto-delete:** OTP/password/phone purged + session message auto-burn in 5 min (configurable) + `🗑️ Delete Now`
- **Rate limit:** 3 gens / hour per user (env `RATE_LIMIT_COUNT` / `WINDOW`)
- **No pyromod:** native `pyrogram` filters + `asyncio.Future` FSM — no blocking leaks
- **Optional MUST_JOIN** channel gate

## 🚀 Quick Start

### 1. Get credentials
- **API_ID / API_HASH:** https://my.telegram.org → *API development tools* → Create app
- **BOT_TOKEN:** https://t.me/BotFather → `/newbot`

### 2. Local run

```bash
cp .env.example .env
# edit .env with your values
pip install -r requirements.txt
python -m bot
```

### 3. Docker

```bash
docker compose up --build -d
docker logs -f zerosess-bot-1
```

### 4. Deploy

#### One-Click Deploy

[![Deploy on Railway](https://railway.app/button.svg)](https://railway.app/template/new?template=https://github.com/saahiyo-cloud/ZeroSess)
[![Deploy to Render](https://render.com/images/deploy-to-render-button.svg)](https://render.com/deploy?repo=https://github.com/saahiyo-cloud/ZeroSess)

> Repository: `https://github.com/saahiyo-cloud/ZeroSess`

**Railway steps:**
1. Push this folder to GitHub
2. Click **Deploy on Railway** → set `API_ID`, `API_HASH`, `BOT_TOKEN` (from `my.telegram.org` / `@BotFather`)
3. Deploy → logs show `✅ Bot started as @...`

- **Railway / Render / Heroku:** Uses `render.yaml` / `Procfile` / `Dockerfile` — just set env vars
- **VPS:** `systemd` + `python -m bot` or Docker

## 📖 User Flow

```
/start → Generate Session → Choose Pyrogram / Telethon
→ API_ID → API_HASH → Phone (+919...) → OTP (12345 or 1 2 3 4 5) → 2FA if needed
→ Session string (Saved Messages + here, auto-delete)
```

Commands: `/start`, `/generate`, `/help`, `/about`, `/ping`, `/id`, `/stats` (owner), `/cancel`, `/destroy`

## ⚙️ Env Vars

| Var | Required | Default | Desc |
|-----|----------|---------|------|
| `API_ID` | yes | — | my.telegram.org |
| `API_HASH` | yes | — | 32 hex |
| `BOT_TOKEN` | yes | — | @BotFather |
| `OWNER_ID` | no | 0 | for /stats |
| `MUST_JOIN` | no | — | @channel |
| `SUPPORT_CHAT` | no | — | shown in /about |
| `SESSION_TIMEOUT` | no | 300 | sec per step |
| `RATE_LIMIT_COUNT` | no | 3 |  |
| `RATE_LIMIT_WINDOW` | no | 3600 | sec |
| `AUTO_DELETE_SECONDS` | no | 300 |  |

## 🛡️ Security Notes

- Never share session strings — they equal account password. Revoke via Telegram → Settings → Devices → Terminate sessions if leaked (`/destroy` guide)
- Run **your own instance** — don't trust public bots with your OTP
- Bot never logs phone/OTP/password/string

## 🧩 Tech Stack

`pyrogram==2.0.106` + `tgcrypto` + `telethon==1.41.2` + `python-dotenv` + `psutil`

## 📁 Structure

```
bot/
  __main__.py      # entry + idle
  config.py        # env validation
  strings.py       # texts + keyboards
  fsm.py           # waiter + rate limit
  generators/
    pyrogram_gen.py
    telethon_gen.py
  plugins/
    start.py       # /start /help callbacks
    generate.py    # wizard
    stats.py
    destroy.py
```

## 🐛 Troubleshooting

- `FloodWait: retry in Xs` → Telegram rate-limit, wait
- `PhoneCodeExpired` → code valid ~5 min, /generate again
- `ApiIdInvalid` → double-check my.telegram.org values (no extra spaces)

---

Built for production — review `bot/plugins/generate.py` for full validation & disconnect-in-finally guarantees.
