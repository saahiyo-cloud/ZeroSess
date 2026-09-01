import logging
import asyncio
# Pyrogram 2.0 import needs a running loop on Python 3.12+/3.14 (asyncio.get_event_loop at import)
try:
    asyncio.get_event_loop()
except RuntimeError:
    asyncio.set_event_loop(asyncio.new_event_loop())

from pyrogram import Client, idle
from pyrogram.enums import ParseMode

from . import config

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
# Silence noisy libs, but keep our logs
logging.getLogger("pyrogram").setLevel(logging.WARNING)
log = logging.getLogger("session-gen")

def build_bot() -> Client:
    config.validate_or_raise()
    bot = Client(
        name="session_gen_bot",
        api_id=config.API_ID,
        api_hash=config.API_HASH,
        bot_token=config.BOT_TOKEN,
        parse_mode=ParseMode.MARKDOWN,
        plugins=dict(root="bot.plugins"),
        workdir=".",
        sleep_threshold=30,
    )
    return bot

async def main():
    bot = build_bot()
    await bot.start()
    me = await bot.get_me()
    log.info(f"✅ Bot started as @{me.username} (id={me.id})")
    log.info(f"   Ping /help /generate ready. Owner={config.OWNER_ID or 'open'}")
    if config.MUST_JOIN:
        log.info(f"   MUST_JOIN={config.MUST_JOIN}")
    await idle()
    await bot.stop()
    log.info("👋 Bot stopped")

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass
    except RuntimeError as e:
        log.error(str(e))
        raise SystemExit(1)
