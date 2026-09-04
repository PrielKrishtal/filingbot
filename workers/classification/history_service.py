from datetime import datetime, timedelta

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from core.database.models import Filing
from core.schemas.enums import TransactionCode
from core.schemas.filing import InsiderHistory


async def get_insider_history(
    session: AsyncSession,
    insider_name: str,
    issuer_cik: str,
    before: datetime,
    current_transaction_code: TransactionCode,
) -> InsiderHistory:

    stmt = select(
        func.count(),
        func.max(Filing.filing_date),
        func.count().filter(
            Filing.transaction_code == TransactionCode.P,
            Filing.filing_date >= (before - timedelta(days=365)),
        ),
        func.count().filter(
            Filing.transaction_code == TransactionCode.S,
            Filing.filing_date >= (before - timedelta(days=365)),
        ),
        func.max(Filing.total_value),
    ).where(
        Filing.insider_name == insider_name,
        Filing.issuer_cik == issuer_cik,
        Filing.filing_date < before,
    )

    result = (await session.execute(stmt)).one()

    total_prior_filings = result[0]
    if result[1] is None:
        days_since_last_trade = None
    else:
        days_since_last_trade = (before - result[1]).days

    purchase_count_12m = result[2]
    sale_count_12m = result[3]
    largest_prior_value = result[4]
    is_first_purchase_after_sales = (
        current_transaction_code == TransactionCode.P
        and purchase_count_12m == 0
        and sale_count_12m > 0
    )

    return InsiderHistory(
        total_prior_filings=total_prior_filings,
        days_since_last_trade=days_since_last_trade,
        purchase_count_12m=purchase_count_12m,
        sale_count_12m=sale_count_12m,
        largest_prior_value=largest_prior_value,
        is_first_purchase_after_sales=is_first_purchase_after_sales,
    )
