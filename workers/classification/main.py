import asyncio
import logging
import math
import socket

import sentry_sdk
from groq import InternalServerError, RateLimitError
from pydantic import ValidationError
from redis.exceptions import TimeoutError
from sqlalchemy import select

from core.database.models import Filing
from core.database.session import AsyncSessionLocal
from core.logging_config import get_logger
from core.redis_client import ack, consume, create_consumer_group, dead_letter, publish
from core.schemas.enums import PipelineStatus
from core.schemas.filing import InsiderFiling
from core.sentry_config import init_sentry
from workers.classification.classifier import classify_filing
from workers.classification.history_service import get_insider_history

base_logger = get_logger("classification")
INITIAL_BACKOFF_SECONDS = 60
MAX_BACKOFF_SECONDS = 30 * 60
MAX_RETRY_AFTER_SECONDS = 24 * 60 * 60
BACKOFF_FACTOR = 2

async def process_classifying(message_id: str, filing_ref: dict[str, str]):
    with sentry_sdk.new_scope() as scope:
        async with AsyncSessionLocal() as session:
            stmt = select(Filing).where(
                Filing.accession_number == filing_ref["accession_number"]
            )
            result = (await session.execute(stmt)).scalar_one()
            history = await get_insider_history(
                session=session,
                insider_name=result.insider_name,
                issuer_cik=result.issuer_cik,
                before=result.filing_date,
                current_transaction_code=result.transaction_code,
            )
            filing = InsiderFiling.model_validate(result)
            log = logging.LoggerAdapter(
                base_logger, extra={"correlation_id": filing.accession_number}
            )
            scope.set_tag("correlation_id", filing_ref["accession_number"])

            try:
                classification = await classify_filing(filing, history)
                result.classification = classification.transaction_classification
                result.classification_reasoning = classification.reasoning
                result.signal_strength = classification.signal_strength
                result.pipeline_status = PipelineStatus.CLASSIFIED
                await session.commit()
                await publish(
                    "filing.classified", {"accession_number": filing.accession_number}
                )

            except ValidationError as e:
                await dead_letter(
                    message=filing_ref["accession_number"],
                    error=str(e),
                    stream="filing.raw",
                    retries=1,
                )
                log.exception("classification failed, sending to dead letter")
                await session.rollback()

            await ack("filing.raw", "classification_group", message_id)


def parse_retry_after(raw_val: str | None) -> float | None:
    if raw_val is None:
        return None

    try:
        seconds = float(raw_val)
    except ValueError:
        return None

    if not math.isfinite(seconds) or seconds <= 0:
        return None

    return min(seconds, MAX_RETRY_AFTER_SECONDS)  # cap the wait time to 24 hours


async def raw_filings_consumer():
    await create_consumer_group("filing.raw", "classification_group")
    current_delay = INITIAL_BACKOFF_SECONDS
    while True:
        try:
            response = await consume(
                groupname="classification_group",
                consumername=socket.gethostname(),
                stream="filing.raw",
                block=4000,
            )
            if not response:
                continue
        except TimeoutError:
            continue

        messages = response[0][1]
        for message_id, fields in messages:
            try:
                await process_classifying(message_id, fields)
                current_delay = INITIAL_BACKOFF_SECONDS

            except (RateLimitError, InternalServerError) as e:
                raw_retry_after = e.response.headers.get("retry-after")
                wait_time = parse_retry_after(raw_retry_after)
                source = "retry-after" if wait_time is not None else "backoff"
                wait_seconds = wait_time if wait_time is not None else current_delay

                base_logger.error(
                    "groq unavailable, pausing classification",
                    extra={
                        "error": type(e).__name__,
                        "wait_seconds": wait_seconds,
                        "source": source,
                    },
                )
                await asyncio.sleep(wait_seconds)

                if source == "backoff":
                    current_delay = min(
                        current_delay * BACKOFF_FACTOR, MAX_BACKOFF_SECONDS
                    )


if __name__ == "__main__":
    init_sentry("classification")
    asyncio.run(raw_filings_consumer())
