from telegram import Update
from telegram.ext import (
    Application,
    ApplicationBuilder,
    CallbackQueryHandler,
    CommandHandler,
    ContextTypes,
)

from core.config import settings
from core.logging_config import get_logger
from telegram_bot.handlers.commands import (
    add,
    handle_alert_mode_choice,
    remove,
    start,
    watchlist,
)

base_logger = get_logger("telegram_bot")


async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE) -> None:
    chat_id = None
    if isinstance(update, Update) and update.effective_chat is not None:
        chat_id = update.effective_chat.id

    base_logger.error(
        "Unhandled exception in Telegram bot",
        exc_info=context.error,
        extra={"chat_id": chat_id},
    )


def build_application() -> Application:
    app = ApplicationBuilder().token(settings.telegram_bot_token).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("watchlist", watchlist))
    app.add_handler(CommandHandler("add", add))
    app.add_handler(CommandHandler("remove", remove))
    app.add_handler(CallbackQueryHandler(handle_alert_mode_choice, pattern=r"^alerts:"))
    app.add_error_handler(error_handler)

    return app


def main() -> None:
    app = build_application()
    base_logger.info("telegram bot starting, polling for updates")
    app.run_polling()


if __name__ == "__main__":
    main()
