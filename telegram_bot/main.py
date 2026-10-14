from telegram import Update
from telegram.ext import (
    Application,
    ApplicationBuilder,
    ApplicationHandlerStop,
    CallbackQueryHandler,
    CommandHandler,
    ContextTypes,
    TypeHandler,
)

from core.config import settings
from core.logging_config import get_logger
from core.redis_client import MAX_COMMANDS_PER_WINDOW, count_command
from core.sentry_config import init_sentry
from telegram_bot.handlers.commands import (
    add,
    handle_alert_mode_choice,
    remove,
    start,
    watchlist,
)

base_logger = get_logger("telegram_bot")
LIMIT_REACHED_MESSAGE = "Let's take a brief pause. To maintain a smooth experience, please wait a moment before sending your next request."

async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE) -> None:
    chat_id = None
    if isinstance(update, Update) and update.effective_chat is not None:
        chat_id = update.effective_chat.id

    base_logger.error(
        "Unhandled exception in Telegram bot",
        exc_info=context.error,
        extra={"chat_id": chat_id},
    )

async def rate_limit_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if update.effective_chat is None:
        return
    
    chat_id = update.effective_chat.id

    is_button_tap = update.callback_query is not None
    is_command = (
                    update.effective_message is not None 
                    and update.effective_message.text is not None 
                    and update.effective_message.text.startswith('/')
                    )
    if not is_button_tap and not is_command:
        return

    num_commands = await count_command(chat_id)

    if num_commands > MAX_COMMANDS_PER_WINDOW:
        if is_button_tap:
            await update.callback_query.answer()

        if num_commands == MAX_COMMANDS_PER_WINDOW+1:
            await update.effective_message.reply_text(LIMIT_REACHED_MESSAGE)

        raise ApplicationHandlerStop
        

    

#TODO: create a custom handler for notifying not supporting images/videos while avoiding 1:1 response per media 
async def media_not_supported_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    pass  
        

def build_application() -> Application:
    app = ApplicationBuilder().token(settings.telegram_bot_token).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("watchlist", watchlist))
    app.add_handler(CommandHandler("add", add))
    app.add_handler(CommandHandler("remove", remove))
    app.add_handler(CallbackQueryHandler(handle_alert_mode_choice, pattern=r"^alerts:"))
    app.add_handler(TypeHandler(Update, rate_limit_handler),group=-1)
    app.add_error_handler(error_handler)

    return app


def main() -> None:
    init_sentry("telegram_bot")
    app = build_application()
    base_logger.info("telegram bot starting, polling for updates")
    app.run_polling()


if __name__ == "__main__":
    main()
