from html import escape

SUCCESS_ICON = "✅"
ERROR_ICON = "⛔"
WATCHLIST_ICON = "📋"
WELCOME_ICON = "👋"

NEW_USER_MESSAGE = f"""{WELCOME_ICON} <b>Welcome to FilingBot</b>
I track SEC Form 4 insider trading filings and alert you when a corporate insider (CEO, CFO, etc.) makes a high-signal buy or sell.

<b>Choose how you want to receive alerts:</b>
• <b>All Companies</b> - every HIGH or MEDIUM signal filing
• <b>Custom List</b> - only the companies you pick

<b>Commands</b>
/watchlist - see your current setting
/add TICKER - add a company (Custom List only)
/remove TICKER - remove a company (Custom List only)"""

RETURNING_USER_MESSAGE = f"""{WELCOME_ICON} <b>Welcome back</b>
You're already registered - alerts are active.
Type /watchlist to see what you're tracking."""

ALL_COMPANIES_CHOSEN_MESSAGE = "Great choice! You'll get alerts for all companies."
CUSTOM_LIST_CHOSEN_MESSAGE = (
    "Great choice! Here's how it works: use /add TICKER and /remove TICKER "
    "to maintain your custom list."
)

NOT_REGISTERED_MESSAGE = f"{ERROR_ICON} <b>Error:</b> please run /start first."
ADD_USAGE_MESSAGE = f"{ERROR_ICON} <b>Usage:</b> /add TICKER"
REMOVE_USAGE_MESSAGE = f"{ERROR_ICON} <b>Usage:</b> /remove TICKER"
TICKERS_UNAVAILABLE_MESSAGE = (
    f"{ERROR_ICON} <b>Error:</b> can't verify tickers right now."
)
INVALID_TICKER_MESSAGE = f"{ERROR_ICON} <b>Error:</b> ticker not valid."
ALL_ALERTS_ADD_MESSAGE = (
    f"{ERROR_ICON} <b>Not needed:</b> you're getting all alerts, so /add isn't needed."
)
ALL_ALERTS_REMOVE_MESSAGE = (
    f"{ERROR_ICON} <b>Nothing to remove:</b> you're getting all alerts."
)
ALREADY_TRACKING_MESSAGE = f"{ERROR_ICON} <b>Already tracking</b> this ticker."

ALL_ALERTS_WATCHLIST_MESSAGE = (
    f"{WATCHLIST_ICON} <b>All companies</b>\n"
    "You're signed up for alerts on ALL companies, so there's no custom list."
)
EMPTY_WATCHLIST_MESSAGE = (
    f"{WATCHLIST_ICON} <b>Your watch list is empty</b>\n"
    "Use /add TICKER to add a company."
)


def watchlist_message(tickers: list[str]) -> str:
    lines = "\n".join(f"• {escape(ticker)}" for ticker in tickers)
    return f"{WATCHLIST_ICON} <b>Your watch list</b>\n{lines}"


def ticker_added_message(ticker: str) -> str:
    return f"{SUCCESS_ICON} <b>Success:</b> {escape(ticker)} added to the watch list"


def ticker_removed_message(ticker: str) -> str:
    return (
        f"{SUCCESS_ICON} <b>Success:</b> {escape(ticker)} removed from the watch list"
    )


def last_ticker_removed_message(ticker: str) -> str:
    return (
        f"{SUCCESS_ICON} <b>Removed:</b> {escape(ticker)}. Your list is now empty, "
        "so you won't get any alerts until you /add one."
    )


def ticker_not_found_message(ticker: str) -> str:
    return f"{ERROR_ICON} <b>Not found:</b> {escape(ticker)} isn't in your watch list"
