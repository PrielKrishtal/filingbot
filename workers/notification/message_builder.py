from datetime import datetime
from decimal import Decimal
from html import escape

from core.database.models import Filing
from core.schemas.enums import TransactionCode

MARKER_BUY = "🟢"
MARKER_SELL = "🔴"
MARKER_NEUTRAL = "⚪"

EDGAR_FILING_INDEX_URL = (
    "https://www.sec.gov/Archives/edgar/data/"
    "{cik}/{accession_no_dashes}/{accession}-index.htm"
)

COMPACT_USD_UNITS = (
    (Decimal(1000000000), "B"),
    (Decimal(1000000), "M"),
    (Decimal(1000), "K"),
)


def build_alert_message(filing: Filing) -> str:
    color_marker, action = describe_transaction(filing.transaction_code)
    preplanned_label = "Yes" if filing.is_10b5_1 else "No"

    headline = (
        f"{color_marker} <b>{filing.signal_strength.value} SIGNAL · "
        f"{escape(filing.issuer_ticker)}</b> — "
        f"{action} {format_compact_usd(filing.total_value)}"
    )
    trade_line = (
        f"{action.capitalize()}: {format_shares(filing.shares_traded)} shares "
        f"@ ${filing.price_per_share:,.2f}"
    )

    lines = [
        headline,
        "",
        f"<b>{escape(filing.insider_name)}</b> — {escape(filing.insider_title)}",
        escape(filing.issuer_name),
        "",
        trade_line,
        f"Holdings after: {format_shares(filing.shares_owned_after)} shares",
        f"Filed: {format_date(filing.filing_date)} · 10b5-1 plan: {preplanned_label}",
        "",
        "<b>Why it matters</b>",
        escape(filing.classification_reasoning),
        "",
        f'<a href="{escape(build_edgar_url(filing))}">View filing on SEC EDGAR →</a>',
    ]
    return "\n".join(lines)


def describe_transaction(code: TransactionCode) -> tuple[str, str]:
    match code:
        case TransactionCode.P:
            return (MARKER_BUY, "BUY")
        case TransactionCode.S:
            return (MARKER_SELL, "SELL")
        case TransactionCode.M:
            return (MARKER_NEUTRAL, "EXERCISE")
        case TransactionCode.A:
            return (MARKER_NEUTRAL, "AWARD")
        case TransactionCode.G:
            return (MARKER_NEUTRAL, "GIFT")
        case TransactionCode.F:
            return (MARKER_NEUTRAL, "WITHHOLD")
        case _:
            raise ValueError(f"no marker/verb defined for {code}")


def format_compact_usd(value: Decimal) -> str:
    for threshold, suffix in COMPACT_USD_UNITS:
        if abs(value) >= threshold:
            return f"${value / threshold:,.1f}{suffix}"
    return f"${value:,.2f}"


def format_shares(shares: Decimal) -> str:
    if shares == shares.to_integral_value():
        return f"{shares:,.0f}"
    return f"{shares.normalize():,f}"


def format_date(moment: datetime) -> str:
    return f"{moment:%b} {moment.day}, {moment.year}"


def build_edgar_url(filing: Filing) -> str:
    return EDGAR_FILING_INDEX_URL.format(
        cik=int(filing.issuer_cik),
        accession_no_dashes=filing.accession_number.replace("-", ""),
        accession=filing.accession_number,
    )
