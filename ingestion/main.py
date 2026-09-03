from contextlib import asynccontextmanager
from core.logging_config import get_logger
from datetime import datetime, timezone
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from fastapi import FastAPI
from ingestion.edgar_poller import poll_new_filings
from core.schemas.filing import InsiderFiling
from core.redis_client import publish,set_value,get_value
from core.database.session import AsyncSessionLocal
from core.database.models import Filing
from sqlalchemy.exc import IntegrityError
from typing import AsyncGenerator
import logging



base_logger = get_logger("ingestion")
since = datetime.now(timezone.utc)
scheduler = AsyncIOScheduler()

@asynccontextmanager
async def ingestion_lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    global since
    last_stored = await get_value("ingestion:last_polled_timestamp")
    if last_stored:
        since = datetime.fromisoformat(last_stored) 
    scheduler.add_job(run_poll_cycle, 'interval', minutes=5)
    scheduler.start()
    yield
    scheduler.shutdown()
    
app = FastAPI(lifespan=ingestion_lifespan)


async def  process_filing(filing:InsiderFiling ):
    log = logging.LoggerAdapter(base_logger, extra={"correlation_id": filing.accession_number})
    log.info("fetched filing")

    db_filing = Filing(**filing.model_dump()) #new filing row
    async with AsyncSessionLocal() as session:
        session.add(db_filing)
        try:
            await session.commit()
            await publish("filing.raw", {"accession_number": filing.accession_number})

        except IntegrityError:          #enforcing idempotency,skip on duplicates
            await session.rollback()
            log.debug("duplicate filing, skipping")

        except Exception:
            await session.rollback()
            log.exception("failed to save filing")

       


async def run_poll_cycle() -> None:
    global since #call to use the global variable initalized above
    filings = await poll_new_filings(since) #get the list of new filings 
    for filing in filings:
        await process_filing(filing)
    since = datetime.now(timezone.utc)
    await set_value("ingestion:last_polled_timestamp", since.isoformat())


@app.get("/health")
async def health_check() -> dict[str, str]:
    return {"status": "healthy"}


@app.post("/poll")
async def manual_poll() -> dict[str, str]:
    await run_poll_cycle()
    return {"status": "success"}







    

