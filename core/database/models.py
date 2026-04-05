from sqlalchemy.orm import Mapped, mapped_column
from core.database.session import Base
from sqlalchemy import Numeric, func, String, Enum, DateTime, BigInteger, JSON, Integer, Date
from decimal import Decimal
from datetime import datetime, date
from typing import Optional
import uuid
from core.schemas.enums import SignalStrength, TransactionCode, TransactionClassification, PipelineStatus

class Filing(Base):
    __tablename__ = "filings"
    id: Mapped[str] = mapped_column(
        String, primary_key=True, default=lambda: str(uuid.uuid4()), index=True
    )
    accession_number: Mapped[str] = mapped_column(String, nullable=False,unique=True)
    filing_date: Mapped[datetime]
    issuer_name: Mapped[str]
    issuer_ticker: Mapped[str]                                
    issuer_cik: Mapped[str]
    insider_name: Mapped[str]
    insider_title: Mapped[str]
    transaction_code: Mapped[TransactionCode] = mapped_column(Enum(TransactionCode))
    shares_traded: Mapped[Decimal]
    price_per_share: Mapped[Decimal]
    total_value: Mapped[Decimal]
    shares_owned_after: Mapped[Decimal]
    is_10b5_1: Mapped[bool]
    signal_strength: Mapped[SignalStrength] = mapped_column(Enum(SignalStrength),nullable=True)
    classification: Mapped[TransactionClassification] = mapped_column(Enum(TransactionClassification),nullable=True)
    classification_reasoning: Mapped[str] = mapped_column(nullable=True)  
    enriched: Mapped[bool] = mapped_column(default=False) 
    summary:  Mapped[str] = mapped_column(nullable=True) 
    chromadb_collection: Mapped[str] = mapped_column(nullable=True) 
    pipeline_status: Mapped[PipelineStatus] = mapped_column(Enum(PipelineStatus),default=PipelineStatus.INGESTED) 
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[Optional[datetime]] = mapped_column(
      DateTime(timezone=True), onupdate=func.now(), nullable=True
    )

   
class User(Base):
    __tablename__ = "users"

    id: Mapped[str] = mapped_column(
        String, primary_key=True, default=lambda: str(uuid.uuid4()), index=True
    )
    telegram_chat_id: Mapped[int] = mapped_column(BigInteger, unique=True)
    username: Mapped[Optional[str]] = mapped_column(nullable=True)
    watchlist: Mapped[list] = mapped_column(JSON, default=list)
    is_active: Mapped[bool] = mapped_column(default=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )


class InsiderProfile(Base):
    __tablename__ = "insider_profiles"

    id: Mapped[str] = mapped_column(
        String, primary_key=True, default=lambda: str(uuid.uuid4()), index=True
    )
    insider_name: Mapped[str]
    issuer_cik: Mapped[str]
    total_filings: Mapped[int] = mapped_column(Integer, default=0)
    last_purchase_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    last_sale_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    purchase_count_12m: Mapped[int] = mapped_column(Integer, default=0)
    sale_count_12m: Mapped[int] = mapped_column(Integer, default=0)
    largest_transaction_value: Mapped[Optional[Decimal]] = mapped_column(Numeric, nullable=True)
    updated_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), onupdate=func.now(), nullable=True
    )