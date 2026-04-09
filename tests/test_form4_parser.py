from datetime import datetime
from decimal import Decimal
from pathlib import Path
from core.schemas.enums import TransactionCode
from ingestion.form4_parser import parse_form4

FIXTURES = Path(__file__).parent / "fixtures"

ACCESSION = "0001234567-26-000001"
FILING_DATE = datetime(2026, 3, 31)


def load(filename: str) -> str:
    return (FIXTURES / filename).read_text()


def test_parse_tesla_option_exercise():
    filing = parse_form4(load("form4_tesla_1318605_2026_purchase.xml"), ACCESSION, FILING_DATE)

    assert filing.issuer_name == "Tesla, Inc."
    assert filing.issuer_ticker == "TSLA"
    assert filing.issuer_cik == "0001318605"
    assert filing.insider_name == "Zhu Xiaotong"
    assert filing.insider_title == "SVP"
    assert filing.transaction_code == TransactionCode.M
    assert filing.shares_traded == Decimal("20000")
    assert filing.price_per_share == Decimal("20.57")
    assert filing.total_value == Decimal("20000") * Decimal("20.57")
    assert filing.shares_owned_after == Decimal("20000")
    assert filing.is_10b5_1 is False


def test_parse_apple_10b5_sale():
    filing = parse_form4(load("form4_apple_0000320193_2026_svp_10b5_sale.xml"), ACCESSION, FILING_DATE)

    assert filing.issuer_name == "Apple Inc."
    assert filing.issuer_ticker == "AAPL"
    assert filing.transaction_code == TransactionCode.M
    assert filing.is_10b5_1 is True


def test_parse_tesla_cfo_exercise_and_sale():
    filing = parse_form4(load("form4_tesla_1318605_2026_cfo_exercise_and_sale.xml"), ACCESSION, FILING_DATE)

    assert filing.issuer_name == "Tesla, Inc."
    assert filing.insider_name == "Taneja Vaibhav"
    assert filing.insider_title == "Chief Financial Officer"
    assert filing.transaction_code == TransactionCode.M
    assert filing.shares_traded == Decimal("6538")


def test_parse_microsoft_tax_withholding():
    filing = parse_form4(load("form4_microsoft_0000789019_2026_evp_tax_withholding.xml"), ACCESSION, FILING_DATE)

    assert filing.issuer_name == "MICROSOFT CORP"
    assert filing.issuer_ticker == "MSFT"
    assert filing.transaction_code == TransactionCode.F
    assert filing.shares_traded == Decimal("31.095")
    assert filing.price_per_share == Decimal("395.55")
    assert filing.is_10b5_1 is False


def test_accession_and_date_passed_through():
    filing = parse_form4(load("form4_tesla_1318605_2026_purchase.xml"), ACCESSION, FILING_DATE)

    assert filing.accession_number == ACCESSION
    assert filing.filing_date == FILING_DATE


def test_total_value_computed_correctly():
    filing = parse_form4(load("form4_microsoft_0000789019_2026_evp_tax_withholding.xml"), ACCESSION, FILING_DATE)

    assert filing.total_value == Decimal("31.095") * Decimal("395.55")



def test_shares_owned_after():
      xml = load("form4_microsoft_0000789019_2026_evp_tax_withholding.xml")

      result = parse_form4(xml, ACCESSION, FILING_DATE)

      assert result.shares_owned_after == Decimal("48576.5643")
