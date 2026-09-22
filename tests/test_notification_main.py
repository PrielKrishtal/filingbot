from datetime import datetime, timezone
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock

from telegram.error import TelegramError

from core.database.models import Filing
from core.schemas.enums import PipelineStatus, SignalStrength, TransactionCode
from workers.notification import main as notification_main

ACCESSION = "0001234567-26-000123"


def make_filing(signal_strength: SignalStrength) -> Filing:
    return Filing(
        accession_number=ACCESSION,
        filing_date=datetime(2026, 9, 7, tzinfo=timezone.utc),
        issuer_name="Acme Corp",
        issuer_ticker="TEST",
        issuer_cik="1234567",
        insider_name="Jane Doe",
        insider_title="Chief Executive Officer",
        transaction_code=TransactionCode.P,
        shares_traded=Decimal(20000),
        price_per_share=Decimal("120.00"),
        total_value=Decimal(2400000),
        shares_owned_after=Decimal(3520000),
        is_10b5_1=False,
        signal_strength=signal_strength,
        classification_reasoning="Voluntary purchase after four consecutive sales.",
    )


class FakeResult:
    """Stands in for the sync Result object `await session.execute(stmt)` returns."""

    def __init__(self, *, scalar_one=None, all_rows=None):
        self._scalar_one = scalar_one
        self._all_rows = all_rows

    def scalar_one(self):
        return self._scalar_one

    def all(self):
        return self._all_rows


class FakeSession:
    """Async-context-manager session stand-in, queued with canned execute() results."""

    def __init__(self, execute_results):
        self._execute_results = list(execute_results)
        self.commit = AsyncMock()
        self.rollback = AsyncMock()

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        return False

    async def execute(self, stmt):
        return self._execute_results.pop(0)


def patch_common(monkeypatch, session):
    monkeypatch.setattr(notification_main, "AsyncSessionLocal", lambda: session)
    # telegram.Bot is a frozen TelegramObject - it blocks attribute reassignment
    # on the real instance, so swap the whole module-level `bot` for a fake instead.
    fake_bot = MagicMock()
    mock_send = AsyncMock()
    fake_bot.send_message = mock_send
    monkeypatch.setattr(notification_main, "bot", fake_bot)
    mock_ack = AsyncMock()
    monkeypatch.setattr(notification_main, "ack", mock_ack)
    mock_dead_letter = AsyncMock()
    monkeypatch.setattr(notification_main, "dead_letter", mock_dead_letter)
    return mock_send, mock_ack, mock_dead_letter


async def test_sends_to_every_registered_user_and_marks_notified(monkeypatch):
    filing = make_filing(SignalStrength.HIGH)
    chat_ids = [111, 222]
    session = FakeSession(
        [
            FakeResult(scalar_one=filing),
            FakeResult(all_rows=[(chat_id, True, []) for chat_id in chat_ids]),
        ]
    )
    mock_send, mock_ack, mock_dead_letter = patch_common(monkeypatch, session)

    await notification_main.process_notification("1-0", {"accession_number": ACCESSION})

    assert mock_send.call_count == 2
    sent_to = {call.kwargs["chat_id"] for call in mock_send.call_args_list}
    assert sent_to == set(chat_ids)
    assert filing.pipeline_status == PipelineStatus.NOTIFIED
    session.commit.assert_called_once()
    mock_dead_letter.assert_not_called()
    mock_ack.assert_called_once_with("filing.classified", "notification_group", "1-0")


async def test_skips_low_signal_without_sending_but_still_persists_status(monkeypatch):
    filing = make_filing(SignalStrength.LOW)
    session = FakeSession([FakeResult(scalar_one=filing)])
    mock_send, mock_ack, _mock_dead_letter = patch_common(monkeypatch, session)

    await notification_main.process_notification("2-0", {"accession_number": ACCESSION})

    mock_send.assert_not_called()
    assert filing.pipeline_status == PipelineStatus.SKIPPED
    mock_ack.assert_called_once_with("filing.classified", "notification_group", "2-0")
    # A status change is only real once committed - mutating the ORM object alone
    # doesn't persist it if the session is never told to commit.
    session.commit.assert_called_once()


async def test_one_blocked_chat_id_does_not_stop_delivery_to_others(monkeypatch):
    filing = make_filing(SignalStrength.MEDIUM)
    chat_ids = [111, 222]
    session = FakeSession(
        [
            FakeResult(scalar_one=filing),
            FakeResult(all_rows=[(chat_id, True, []) for chat_id in chat_ids]),
        ]
    )
    mock_send, mock_ack, mock_dead_letter = patch_common(monkeypatch, session)
    mock_send.side_effect = [TelegramError("bot was blocked by the user"), None]

    await notification_main.process_notification("3-0", {"accession_number": ACCESSION})

    assert mock_send.call_count == 2
    assert filing.pipeline_status == PipelineStatus.NOTIFIED
    session.commit.assert_called_once()
    mock_dead_letter.assert_not_called()
    mock_ack.assert_called_once()


async def test_filters_by_alert_mode_and_watchlist(monkeypatch):
    filing = make_filing(SignalStrength.HIGH)  # issuer_ticker="TEST"
    session = FakeSession(
        [
            FakeResult(scalar_one=filing),
            FakeResult(
                all_rows=[
                    (111, True, []),  # all-mode: gets everything
                    (222, False, ["TEST"]),  # custom-mode, ticker matches
                    (333, False, ["OTHER"]),  # custom-mode, ticker doesn't match
                ]
            ),
        ]
    )
    mock_send, mock_ack, mock_dead_letter = patch_common(monkeypatch, session)

    await notification_main.process_notification("5-0", {"accession_number": ACCESSION})

    sent_to = {call.kwargs["chat_id"] for call in mock_send.call_args_list}
    assert sent_to == {111, 222}
    assert filing.pipeline_status == PipelineStatus.NOTIFIED
    session.commit.assert_called_once()
    mock_dead_letter.assert_not_called()
    mock_ack.assert_called_once_with("filing.classified", "notification_group", "5-0")


async def test_dead_letters_when_message_building_fails_on_bad_data(monkeypatch):
    filing = make_filing(SignalStrength.HIGH)
    session = FakeSession([FakeResult(scalar_one=filing)])
    mock_send, mock_ack, mock_dead_letter = patch_common(monkeypatch, session)
    monkeypatch.setattr(
        notification_main,
        "build_alert_message",
        MagicMock(side_effect=TypeError("classification_reasoning is None")),
    )

    await notification_main.process_notification("4-0", {"accession_number": ACCESSION})

    mock_send.assert_not_called()
    mock_dead_letter.assert_called_once_with(
        message=ACCESSION,
        error="classification_reasoning is None",
        stream="filing.classified",
        retries=1,
    )
    session.rollback.assert_called_once()
    session.commit.assert_not_called()
    # A dead-lettered message must still be acked - otherwise it sits pending forever.
    mock_ack.assert_called_once_with("filing.classified", "notification_group", "4-0")
