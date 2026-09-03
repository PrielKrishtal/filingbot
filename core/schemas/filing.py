from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel

from core.schemas.enums import (
    SignalStrength,
    TransactionClassification,
    TransactionCode,
)


class InsiderFiling(BaseModel):
    accession_number: str
    filing_date: datetime                                   
    issuer_name: str                                      
    issuer_ticker: str                                    
    issuer_cik: str
    insider_name: str
    insider_title: str
    transaction_code: TransactionCode
    shares_traded: Decimal
    price_per_share: Decimal
    total_value: Decimal
    shares_owned_after: Decimal
    is_10b5_1: bool


class ClassificationResult(BaseModel):
    signal_strength: SignalStrength
    transaction_classification: TransactionClassification
    reasoning: str
    enrich: bool