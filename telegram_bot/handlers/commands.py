from httpx import HTTPError
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import ContextTypes

from core.database.models import User
from core.database.session import AsyncSessionLocal
from core.logging_config import get_logger
from core.ticker_directory import get_valid_tickers

base_logger = get_logger("telegram_bot")
NEW_USER_MESSAGE = """👋 <b>Welcome to FilingBot</b>
I track SEC Form 4 insider trading filings and alert you when a corporate insider (CEO, CFO, etc.) makes a high-signal buy or sell.

<b>Choose how you want to receive alerts:</b>
• <b>All Companies</b> - every HIGH or MEDIUM signal filing
• <b>Custom List</b> - only the companies you pick

<b>Commands</b>
/watchlist - see your current setting
/add TICKER - add a company (Custom List only)
/remove TICKER - remove a company (Custom List only)"""


RETURNING_USER_MESSAGE = """👋 <b>Welcome back</b>
You're already registered - alerts are active.
Type /watchlist to see what you're tracking."""

ALL_COMPANIES_CHOSEN_MESSAGE = "Great choice! You'll get alerts for all companies."

CUSTOM_LIST_CHOSEN_MESSAGE = (
    "Great choice! Here's how it works: use /add TICKER and /remove TICKER "
    "to maintain your custom list."
)


ALERT_MODE_KEYBOARD = InlineKeyboardMarkup(
    [
        [
            InlineKeyboardButton("All Companies", callback_data="alerts:all"),
            InlineKeyboardButton("Custom List", callback_data="alerts:custom"),
        ]
    ]
)


async def get_registered_user(session: AsyncSession, update: Update) -> User | None:
    chat_id = update.effective_chat.id
    stmt = select(User).where(User.telegram_chat_id == chat_id)
    user = (await session.execute(stmt)).scalar_one_or_none()

    if user is None:
        base_logger.warning(f"User {chat_id} not registered")
        await update.effective_message.reply_text("Please run /start first.")
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
        text = (
            "You're signed up for alerts on ALL companies, so there's no custom list."
        )

    elif user_watch_list == []:
        text = "Your list is empty. Use /add TICKER to add a company."

    else:
        text = "Your Watch List is: " + ", ".join(user_watch_list)

    await update.message.reply_text(text)


async def add(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:

    if not context.args:
        await update.message.reply_text("Usage: /add TICKER")
        return

    new_ticker = context.args[0].strip().upper()

    try:
        valid_tickers = await get_valid_tickers()

    except HTTPError:
        await update.message.reply_text("can't verify tickers right now")
        base_logger.exception("Error - during get_valid_tickers() ")
        return

    if new_ticker not in valid_tickers:
        await update.message.reply_text("Error: TICKER name not valid")
        return

    async with AsyncSessionLocal() as session:
        current_user = await get_registered_user(session, update)

        if current_user is None:
            return

        if current_user.alerts_all:
            await update.message.reply_text(
                "You're getting all alerts, so /add isn't needed."
            )
            return

        if new_ticker in current_user.watchlist:
            await update.message.reply_text("You're already tracking this TICKER")
            return

        current_user.watchlist = [*current_user.watchlist, new_ticker]
        await session.commit()
        await update.message.reply_text(
            f"Success: {new_ticker} added to the watch list"
        )


async def remove(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not context.args:
        await update.message.reply_text("Usage: /remove TICKER")
        return

    ticker_to_remove = context.args[0].strip().upper()

    async with AsyncSessionLocal() as session:
        current_user = await get_registered_user(session, update)

        if current_user is None:
            return

        if current_user.alerts_all:
            await update.message.reply_text(
                "You're getting all alerts, so there's nothing to remove."
            )
            return

        if ticker_to_remove not in current_user.watchlist:
            await update.message.reply_text(
                f"{ticker_to_remove} isn't in your watchlist"
            )
            return

        current_user.watchlist = [
            t for t in current_user.watchlist if t != ticker_to_remove
        ]
        await session.commit()
        if not current_user.watchlist:
            text = (
                f"Removed {ticker_to_remove}. Your list is now empty, so you won't "
                "get any alerts until you /add one."
            )
        else:
            text = f"Success: {ticker_to_remove} removed from the watch list"

        await update.message.reply_text(text)
