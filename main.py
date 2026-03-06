from src.agents.assistant_runtime import WingmanRuntime
from src.integrations.telegram import build_telegram_application

runtime = WingmanRuntime()
app = build_telegram_application(ask_fn=runtime.ask)
app.run_polling()
