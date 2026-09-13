import asyncio
import logging
import socket

from pydantic import ValidationError
from redis.exceptions import TimeoutError
from sqlalchemy import select

from core.database.models import Filing
from core.database.session import AsyncSessionLocal
from core.logging_config import get_logger
from core.redis_client import ack, consume, create_consumer_group, dead_letter, publish
from core.schemas.enums import PipelineStatus
from core.schemas.filing import InsiderFiling
from workers.classification.classifier import classify_filing
from workers.classification.history_service import get_insider_history

base_logger = get_logger("classification")


async def process_classifying(message_id: str, filing_ref: dict[str, str]):
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

        try:
            classification = await classify_filing(filing, history)
            result.classification = classification.transaction_classification
            result.classification_reasoning = classification.reasoning
            result.signal_strength = classification.signal_strength
            result.enriched = classification.enrich
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


async def raw_filings_consumer():
    await create_consumer_group("filing.raw", "classification_group")
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
            await process_classifying(message_id, fields)


if __name__ == "__main__":
    asyncio.run(raw_filings_consumer())
