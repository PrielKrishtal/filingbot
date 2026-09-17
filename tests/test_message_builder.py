from datetime import datetime, timezone
from decimal import Decimal

import pytest

from core.database.models import Filing
from core.schemas.enums import SignalStrength, TransactionCode
from workers.notification.message_builder import (
    MARKER_BUY,
    MARKER_NEUTRAL,
    MARKER_SELL,
    build_alert_message,
    build_edgar_url,
    describe_transaction,
    format_compact_usd,
    format_date,
    format_shares,
)


@pytest.mark.parametrize(
    "code, expected_tuple",
    [
        (TransactionCode.P, (MARKER_BUY, "BUY")),
        (TransactionCode.S, (MARKER_SELL, "SELL")),
        (TransactionCode.M, (MARKER_NEUTRAL, "EXERCISE")),
        (TransactionCode.A, (MARKER_NEUTRAL, "AWARD")),
        (TransactionCode.G, (MARKER_NEUTRAL, "GIFT")),
        (TransactionCode.F, (MARKER_NEUTRAL, "WITHHOLD")),
    ],
)
def test_describe_transaction(code: TransactionCode, expected_tuple: tuple[str, str]):
    assert describe_transaction(code) == expected_tuple


def test_describe_transaction_unknown_code_raises():
    with pytest.raises(ValueError, match="no marker/verb defined"):
        describe_transaction("Test")


@pytest.mark.parametrize(
    "value, expected",
    [
        (Decimal(500), "$500.00"),
        (Decimal(15300), "$15.3K"),
        (Decimal(2400000), "$2.4M"),
        (Decimal(1250000000), "$1.2B"),
    ],
)
def test_format_compact_usd(value, expected):
    assert format_compact_usd(value) == expected


def test_format_shares():
    assert format_shares(Decimal("20000.00")) == "20,000"
    assert format_shares(Decimal("1234.5000")) == "1,234.5"


def test_format_date():
    assert format_date(datetime(2026, 9, 7, tzinfo=timezone.utc)) == "Sep 7, 2026"
    assert format_date(datetime(2026, 12, 31, tzinfo=timezone.utc)) == "Dec 31, 2026"


def test_build_edgar_url():
    filing = Filing(
        issuer_cik="1234567",
        accession_number="0001234567-26-000123",
    )
    assert build_edgar_url(filing) == (
        "https://www.sec.gov/Archives/edgar/data/"
        "1234567/000123456726000123/0001234567-26-000123-index.htm"
    )


def test_build_alert_message_escapes_and_full_output():
    filing = Filing(
        transaction_code=TransactionCode.P,
        signal_strength=SignalStrength.HIGH,
        issuer_ticker="TEST",
        issuer_name="Acme & Co",
        insider_name="Jane <Doe>",
        insider_title="Chief Executive Officer",
        total_value=Decimal(2400000),
        shares_traded=Decimal(20000),
        price_per_share=Decimal("120.00"),
        shares_owned_after=Decimal(3520000),
        filing_date=datetime(2026, 9, 7, tzinfo=timezone.utc),
        is_10b5_1=False,
        classification_reasoning="Voluntary purchase after four consecutive sales.",
        issuer_cik="1234567",
        accession_number="0001234567-26-000123",
    )

    message = build_alert_message(filing)

    # unescaped input never appears raw in HTML output
    assert "Acme & Co" not in message
    assert "<Doe>" not in message
    assert "Acme &amp; Co" in message
    assert "Jane &lt;Doe&gt;" in message
    assert "TEST" in message
    assert "BUY" in message
    assert "$2.4M" in message
    assert "20,000 shares" in message
    assert "3,520,000 shares" in message
    assert "Sep 7, 2026" in message
    assert "10b5-1 plan: No" in message
    assert filing.classification_reasoning in message
    assert "0001234567-26-000123-index.htm" in message
