import logging

from src.agents.assistant_runtime import WingmanRuntime
from src.integrations.telegram import build_telegram_application

logging.basicConfig(
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger("wingman.telegram.bootstrap")

logger.info("Initializing runtime...")
runtime = WingmanRuntime()
logger.info("Building Telegram application...")
app = build_telegram_application(ask_fn=runtime.ask)
logger.info("Starting polling. Bot is ready.")
app.run_polling()

