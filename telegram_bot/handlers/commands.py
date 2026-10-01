from httpx import HTTPError
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import ContextTypes

from core.database.models import User
from core.database.session import AsyncSessionLocal
from core.logging_config import get_logger
from core.ticker_directory import get_valid_tickers
from telegram_bot.messages import (
    ADD_USAGE_MESSAGE,
    ALL_ALERTS_ADD_MESSAGE,
    ALL_ALERTS_REMOVE_MESSAGE,
    ALL_ALERTS_WATCHLIST_MESSAGE,
    ALL_COMPANIES_CHOSEN_MESSAGE,
    ALREADY_TRACKING_MESSAGE,
    CUSTOM_LIST_CHOSEN_MESSAGE,
    EMPTY_WATCHLIST_MESSAGE,
    INVALID_TICKER_MESSAGE,
    NEW_USER_MESSAGE,
    NOT_REGISTERED_MESSAGE,
    REMOVE_USAGE_MESSAGE,
    RETURNING_USER_MESSAGE,
    TICKERS_UNAVAILABLE_MESSAGE,
    last_ticker_removed_message,
    ticker_added_message,
    ticker_not_found_message,
    ticker_removed_message,
    watchlist_message,
)

base_logger = get_logger("telegram_bot")

ALERT_MODE_KEYBOARD = InlineKeyboardMarkup(
    [
        [
            InlineKeyboardButton("All Companies", callback_data="alerts:all"),
            InlineKeyboardButton("Custom List", callback_data="alerts:custom"),
        ]
    ]
)


async def reply_html(update: Update, text: str) -> None:
    await update.effective_message.reply_text(text, parse_mode="HTML")


async def get_registered_user(session: AsyncSession, update: Update) -> User | None:
    chat_id = update.effective_chat.id
    stmt = select(User).where(User.telegram_chat_id == chat_id)
    user = (await session.execute(stmt)).scalar_one_or_none()

    if user is None:
        base_logger.warning(f"User {chat_id} not registered")
        await reply_html(update, NOT_REGISTERED_MESSAGE)
        return None

    return user


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    async with AsyncSessionLocal() as session:
        stmt = select(User).where(User.telegram_chat_id == update.effective_chat.id)
        current_user = (await session.execute(stmt)).scalar_one_or_none()

        if not current_user:
            session.add(
                User(
                    telegram_chat_id=update.effective_chat.id,
                    username=update.effective_user.username,
                )
            )
            await session.commit()

    text = NEW_USER_MESSAGE if not current_user else RETURNING_USER_MESSAGE
    keyboard = ALERT_MODE_KEYBOARD if not current_user else None
    await update.message.reply_text(text, reply_markup=keyboard, parse_mode="HTML")


async def handle_alert_mode_choice(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> None:
    choice = update.callback_query.data
    await update.callback_query.answer()
    await update.callback_query.edit_message_reply_markup(
        reply_markup=None
    )  # remove only buttons

    async with AsyncSessionLocal() as session:
        current_user = await get_registered_user(session, update)

        if current_user is None:
            return

        if choice == "alerts:custom":
            current_user.alerts_all = False
        else:
            current_user.alerts_all = True
        await session.commit()

    button_response = (
        CUSTOM_LIST_CHOSEN_MESSAGE
        if choice == "alerts:custom"
        else ALL_COMPANIES_CHOSEN_MESSAGE
    )
    await update.callback_query.message.reply_text(button_response)


async def watchlist(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    async with AsyncSessionLocal() as session:
        stmt = select(User.alerts_all, User.watchlist).where(
            User.telegram_chat_id == update.effective_chat.id
        )
        row = (await session.execute(stmt)).one_or_none()

    if row is None:
        await start(update, context)
        return

    user_alert_all, user_watch_list = row

    if user_alert_all:
        text = ALL_ALERTS_WATCHLIST_MESSAGE

    elif not user_watch_list:
        text = EMPTY_WATCHLIST_MESSAGE

    else:
        text = watchlist_message(user_watch_list)

    await reply_html(update, text)


async def add(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:

    if not context.args:
        await reply_html(update, ADD_USAGE_MESSAGE)
        return

    new_ticker = context.args[0].strip().upper()

    try:
        valid_tickers = await get_valid_tickers()

    except HTTPError:
        await reply_html(update, TICKERS_UNAVAILABLE_MESSAGE)
        base_logger.exception("Error - during get_valid_tickers() ")
        return

    if new_ticker not in valid_tickers:
        await reply_html(update, INVALID_TICKER_MESSAGE)
        return

    async with AsyncSessionLocal() as session:
        current_user = await get_registered_user(session, update)

        if current_user is None:
            return

        if current_user.alerts_all:
            await reply_html(update, ALL_ALERTS_ADD_MESSAGE)
            return

        if new_ticker in current_user.watchlist:
            await reply_html(update, ALREADY_TRACKING_MESSAGE)
            return

        current_user.watchlist = [*current_user.watchlist, new_ticker]
        await session.commit()
        await reply_html(update, ticker_added_message(new_ticker))


async def remove(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not context.args:
        await reply_html(update, REMOVE_USAGE_MESSAGE)
        return

    ticker_to_remove = context.args[0].strip().upper()

    async with AsyncSessionLocal() as session:
        current_user = await get_registered_user(session, update)

        if current_user is None:
            return

        if current_user.alerts_all:
            await reply_html(update, ALL_ALERTS_REMOVE_MESSAGE)
            return

        if ticker_to_remove not in current_user.watchlist:
            await reply_html(update, ticker_not_found_message(ticker_to_remove))
            return

        current_user.watchlist = [
            t for t in current_user.watchlist if t != ticker_to_remove
        ]
        await session.commit()
        if not current_user.watchlist:
            text = last_ticker_removed_message(ticker_to_remove)
        else:
            text = ticker_removed_message(ticker_to_remove)

        await reply_html(update, text)
