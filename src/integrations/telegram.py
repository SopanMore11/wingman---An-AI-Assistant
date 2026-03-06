import os
import uuid
from collections.abc import Awaitable, Callable, Iterable

from telegram import Update
from telegram.constants import ChatAction
from telegram.ext import Application, CommandHandler, ContextTypes, MessageHandler, filters

MAX_TELEGRAM_MESSAGE_LEN = 4000

AskFn = Callable[[str, str, str], Awaitable[str]]


def _chunk_text(text: str, max_len: int = MAX_TELEGRAM_MESSAGE_LEN) -> Iterable[str]:
    if len(text) <= max_len:
        yield text
        return

    start = 0
    while start < len(text):
        end = min(start + max_len, len(text))
        if end < len(text):
            split_at = text.rfind("\n", start, end)
            if split_at > start:
                end = split_at
        chunk = text[start:end].strip() or text[start:end]
        yield chunk
        start = end


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    del context
    if update.message is None:
        return

    await update.message.reply_text(
        "Bot is online. Send any message and I will forward it to the orchestrator."
    )


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    del context
    if update.message is None:
        return

    await update.message.reply_text(
        "Commands:\n"
        "/start - Start the bot\n"
        "/help - Show this help"
    )


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if update.message is None or not update.message.text:
        return

    chat = update.effective_chat
    user = update.effective_user

    user_id = str(user.id if user else "unknown_user")
    session_chat_id = str(chat.id if chat else uuid.uuid4().hex)
    session_id = f"tg_chat_{session_chat_id}"

    ask_fn: AskFn = context.application.bot_data["ask_fn"]

    await update.message.chat.send_action(ChatAction.TYPING)
    response_text = await ask_fn(
        user_id=user_id,
        session_id=session_id,
        text=update.message.text,
    )

    for part in _chunk_text(response_text):
        await update.message.reply_text(part)


def build_telegram_application(
    ask_fn: AskFn,
    token: str | None = None,
) -> Application:
    resolved_token = token or os.getenv("TELEGRAM_BOT_TOKEN")
    if not resolved_token:
        raise RuntimeError("Missing TELEGRAM_BOT_TOKEN in environment variables.")

    application = Application.builder().token(resolved_token).build()
    application.bot_data["ask_fn"] = ask_fn
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    return application


def run(ask_fn: AskFn) -> None:
    application = build_telegram_application(ask_fn=ask_fn)
    print("Telegram bot is running... Press Ctrl+C to stop.")
    application.run_polling()
