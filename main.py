import warnings
import logging
from langsmith.integrations.google_adk import configure_google_adk

# Ignore all warnings (per user request)
warnings.filterwarnings("ignore")

# Basic logging configuration for visible logs when running `main.py`
logging.basicConfig(
	level=logging.INFO,
	format="%(asctime)s %(levelname)s %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)
logger.info("Configuring Wingman runtime and Telegram application")

from src.agents.wingman_runtime import WingmanRuntime
from src.integrations.telegram import build_telegram_application


def main() -> None:
	configure_google_adk()
	runtime = WingmanRuntime()
	app = build_telegram_application(ask_fn=runtime.ask)
	logger.info("Starting Telegram polling")
	app.run_polling()


if __name__ == "__main__":
	main()
