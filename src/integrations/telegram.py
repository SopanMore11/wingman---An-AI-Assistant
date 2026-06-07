import os
import uuid
from collections.abc import Awaitable, Callable, Iterable
import html
import logging
import re

from telegram import Update
from telegram.constants import ChatAction, ParseMode
from telegram.error import BadRequest
from telegram.ext import Application, CommandHandler, ContextTypes, MessageHandler, filters

MAX_TELEGRAM_MESSAGE_LEN = 4000
logger = logging.getLogger("wingman.telegram")

AskFn = Callable[[str, str, str], Awaitable[str]]

_PLACEHOLDER_RE = re.compile(r"\ue000(\d+)\ue001")
_FENCED_CODE_RE = re.compile(r"```(?:[a-zA-Z0-9_+-]+)?\n?(.*?)```", re.DOTALL)
_INLINE_CODE_RE = re.compile(r"`([^`\n]+)`")
_SAFE_HTML_TAG_RE = re.compile(
    r"</?(?:b|strong|i|em|u|s|strike|del|code|pre)>"
    r"|<a\s+href=(?:\"[^\"]*\"|'[^']*')>"
    r"|</a>",
    re.IGNORECASE,
)


def _store_placeholder(tokens: list[str], value: str) -> str:
    tokens.append(value)
    return f"\ue000{len(tokens) - 1}\ue001"


def _restore_placeholders(text: str, tokens: list[str]) -> str:
    def replace(match: re.Match[str]) -> str:
        index = int(match.group(1))
        return tokens[index] if 0 <= index < len(tokens) else match.group(0)

    return _PLACEHOLDER_RE.sub(replace, text)


def _markdown_to_telegram_html(text: str) -> str:
    """Convert common model Markdown into Telegram-safe HTML."""
    tokens: list[str] = []

    def replace_fenced_code(match: re.Match[str]) -> str:
        code = html.escape(match.group(1).strip(), quote=False)
        return _store_placeholder(tokens, f"<pre>{code}</pre>")

    def replace_inline_code(match: re.Match[str]) -> str:
        code = html.escape(match.group(1), quote=False)
        return _store_placeholder(tokens, f"<code>{code}</code>")

    def protect_html_tag(match: re.Match[str]) -> str:
        return _store_placeholder(tokens, match.group(0))

    text = _FENCED_CODE_RE.sub(replace_fenced_code, text)
    text = _INLINE_CODE_RE.sub(replace_inline_code, text)
    text = _SAFE_HTML_TAG_RE.sub(protect_html_tag, text)
    text = html.escape(text, quote=False)

    text = re.sub(r"(?m)^#{1,6}\s+(.+)$", r"<b>\1</b>", text)
    text = re.sub(r"\[([^\]\n]+)\]\((https?://[^)\s]+)\)", r'<a href="\2">\1</a>', text)
    text = re.sub(r"\*\*([^*\n][\s\S]*?[^*\n])\*\*", r"<b>\1</b>", text)
    text = re.sub(r"__([^_\n][\s\S]*?[^_\n])__", r"<b>\1</b>", text)

    return _restore_placeholders(text, tokens)


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
    logger.info("Handled /start command")


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    del context
    if update.message is None:
        return

    await update.message.reply_text(
        "Commands:\n"
        "/start - Start the bot\n"
        "/help - Show this help"
    )
    logger.info("Handled /help command")


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if update.message is None or not update.message.text:
        return

    chat = update.effective_chat
    user = update.effective_user

    user_id = str(user.id if user else "unknown_user")
    session_chat_id = str(chat.id if chat else uuid.uuid4().hex)
    session_id = f"tg_chat_{session_chat_id}"
    logger.info("Incoming message | user_id=%s | chat_id=%s", user_id, session_chat_id)

    ask_fn: AskFn = context.application.bot_data["ask_fn"]

    await update.message.chat.send_action(ChatAction.TYPING)
    response_text = await ask_fn(
        user_id=user_id,
        session_id=session_id,
        text=update.message.text,
    )
    logger.info("Orchestrator response received | user_id=%s | chars=%s", user_id, len(response_text))

    telegram_html = _markdown_to_telegram_html(response_text)

    for part in _chunk_text(telegram_html):
        try:
            await update.message.reply_text(part, parse_mode=ParseMode.HTML)
        except BadRequest as exc:
            logger.warning("HTML parse failed; sending plain text fallback: %s", exc)
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
    logger.info("Telegram application built with command and message handlers")
    return application


def run(ask_fn: AskFn) -> None:
    application = build_telegram_application(ask_fn=ask_fn)
    print("Telegram bot is running... Press Ctrl+C to stop.")
    application.run_polling()
