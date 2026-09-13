import json
from datetime import datetime, timezone
from decimal import Decimal
from pathlib import Path
from unittest.mock import AsyncMock

import pytest
from pydantic import ValidationError

from core.schemas.filing import InsiderHistory
from ingestion.form4_parser import parse_form4
from workers.classification import classifier
from workers.classification.classifier import classify_filing
from workers.classification.prompts import build_corrective_prompt, build_user_prompt

FIXTURES = Path(__file__).parent / "fixtures"
ACCESSION = "0001234567-26-000001"
FILING_DATE = datetime(2026, 3, 31, tzinfo=timezone.utc)

def load(filename: str) -> str:
    return (FIXTURES / filename).read_text()


def test_build_user_prompt_includes_key_values():
    filing = parse_form4(load("form4_tesla_1318605_2026_purchase.xml"), ACCESSION, FILING_DATE)
    history = InsiderHistory(
            total_prior_filings=3,
            days_since_last_trade=340,
            purchase_count_12m=0,
            sale_count_12m=3,
            largest_prior_value=Decimal(50000),
            is_first_purchase_after_sales=True,
        )
    prompt = build_user_prompt(filing,history)
    assert filing.insider_name in prompt
    assert filing.insider_title in prompt
    assert str(filing.shares_traded) in prompt
    assert str(history.sale_count_12m) in prompt
    assert str(history.is_first_purchase_after_sales) in prompt




def test_build_corrective_prompt_includes_error():
    previous_response = '{"signal_strength": "SUPER_HIGH", "reasoning": "looks good"}'
    error = "signal_strength: Input should be 'HIGH', 'MEDIUM', 'LOW' or 'NOISE'"
    prompt = build_corrective_prompt(previous_response,error)
    assert previous_response in prompt 
    assert error in prompt


async def test_classify_filing_success(monkeypatch):
    filing = parse_form4(load("form4_tesla_1318605_2026_purchase.xml"), ACCESSION, FILING_DATE)
    history = InsiderHistory(
                total_prior_filings=3,
                days_since_last_trade=340,
                purchase_count_12m=0,
                sale_count_12m=3,
                largest_prior_value=Decimal(50000),
                is_first_purchase_after_sales=True,
            )

    canned_response = json.dumps({
        "signal_strength": "HIGH",
        "transaction_classification": "voluntary_purchase",
        "reasoning": "insider bought after a run of sales",
        "enrich": True,
    })

    mock_call_groq = AsyncMock(return_value=canned_response)
    monkeypatch.setattr(classifier, "_call_groq", mock_call_groq)

    result = await classify_filing(filing, history)

    assert result.signal_strength.value == "HIGH"
    assert result.transaction_classification.value == "voluntary_purchase"
    assert result.enrich is True
    mock_call_groq.assert_called_once()


async def test_classify_filing_retries_then_succeeds(monkeypatch):
    filing = parse_form4(load("form4_tesla_1318605_2026_purchase.xml"), ACCESSION, FILING_DATE)
    history = InsiderHistory(
        total_prior_filings=3,
        days_since_last_trade=340,
        purchase_count_12m=0,
        sale_count_12m=3,
        largest_prior_value=Decimal(50000),
        is_first_purchase_after_sales=True,
    )

    invalid_response = '{"signal_strength": "SUPER_HIGH", "reasoning": "looks good"}'
    valid_response = json.dumps({
        "signal_strength": "HIGH",
        "transaction_classification": "voluntary_purchase",
        "reasoning": "insider bought after a run of sales",
        "enrich": True,
    })

    mock_call_groq = AsyncMock(side_effect=[invalid_response, valid_response])
    monkeypatch.setattr(classifier, "_call_groq", mock_call_groq)

    result = await classify_filing(filing, history)

    assert result.signal_strength.value == "HIGH"
    assert mock_call_groq.call_count == 2


async def test_classify_filing_raises_after_retry_fails(monkeypatch):
    filing = parse_form4(load("form4_tesla_1318605_2026_purchase.xml"), ACCESSION, FILING_DATE)
    history = InsiderHistory(
        total_prior_filings=3,
        days_since_last_trade=340,
        purchase_count_12m=0,
        sale_count_12m=3,
        largest_prior_value=Decimal(50000),
        is_first_purchase_after_sales=True,
    )

    invalid_response = '{"signal_strength": "SUPER_HIGH", "reasoning": "looks good"}'

    mock_call_groq = AsyncMock(side_effect=[invalid_response, invalid_response])
    monkeypatch.setattr(classifier, "_call_groq", mock_call_groq)

    with pytest.raises(ValidationError):
        await classify_filing(filing, history)

    assert mock_call_groq.call_count == 2