from datetime import datetime, timedelta, timezone

import httpx

from core.config import settings
from core.logging_config import get_logger

base_logger = get_logger("ticker_directory")

SEC_TICKER_LIST_URL = "https://www.sec.gov/files/company_tickers.json"
TICKER_HEADERS = {"User-Agent": settings.sec_user_agent}
CACHE_TTL = timedelta(hours=24)
REQUEST_TIMEOUT_SECONDS = 15.0

_valid_tickers: set[str] | None = None
_loaded_at: datetime | None = None


async def get_valid_tickers() -> set[str]:
    global _valid_tickers, _loaded_at

    now = datetime.now(timezone.utc)
    cache_is_fresh = (
        _valid_tickers is not None
        and _loaded_at is not None
        and now - _loaded_at < CACHE_TTL
    )
    if cache_is_fresh:
        return _valid_tickers

    try:
        _valid_tickers = await _download_tickers()
    except httpx.HTTPError as error:
        if _valid_tickers is None:
            raise
        base_logger.warning(f"ticker refresh failed, serving stale cache: {error}")
        return _valid_tickers

    _loaded_at = now
    return _valid_tickers


async def _download_tickers() -> set[str]:
    async with httpx.AsyncClient(timeout=REQUEST_TIMEOUT_SECONDS) as client:
        response = await client.get(SEC_TICKER_LIST_URL, headers=TICKER_HEADERS)
    response.raise_for_status()
    return {entry["ticker"].upper() for entry in response.json().values()}
