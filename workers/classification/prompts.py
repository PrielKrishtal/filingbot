from core.schemas.filing import InsiderFiling, InsiderHistory

SYSTEM_PROMPT = """You are a financial filing analyst. You receive insider trading data
from a SEC Form 4 filing, plus that insider's trading history at the same company.
Classify whether this transaction signals insider confidence or is routine/administrative.

Consider:
1. Transaction code — P=purchase, S=sale, M=option exercise, A=award/grant, G=gift, F=tax withholding.
2. Insider title — CEO/CFO/COO/President carry the highest signal.
3. Dollar value — above $100K is notable, above $500K is very significant.
4. 10b5-1 flag — if set, this was pre-planned, lower signal.
5. History — a first purchase after a run of sales is a strong signal; routine repeated purchases are lower signal.

signal_strength must be one of: HIGH, MEDIUM, LOW, NOISE.
transaction_classification must be one of: voluntary_purchase, option_exercise, planned_sale, tax_disposition, gift, other.
"""


def build_user_prompt(filing: InsiderFiling, history: InsiderHistory) -> str:
    return f"""Insider: {filing.insider_name}, {filing.insider_title}
Transaction: {filing.transaction_code.value}, {filing.shares_traded} shares at ${filing.price_per_share}, total ${filing.total_value}
10b5-1 plan: {filing.is_10b5_1}

History at this company:
- Prior filings: {history.total_prior_filings}
- Days since last trade: {history.days_since_last_trade}
- Purchases in last 12 months: {history.purchase_count_12m}
- Sales in last 12 months: {history.sale_count_12m}
- Largest prior transaction value: {history.largest_prior_value}
- First purchase after a run of sales: {history.is_first_purchase_after_sales}
"""


def build_corrective_prompt(previous_response: str, error: str) -> str:
    return f"""Your previous response did not match the required schema.

Your response was:
{previous_response}

Validation error:
{error}

Respond again with valid JSON matching the schema exactly.
"""
