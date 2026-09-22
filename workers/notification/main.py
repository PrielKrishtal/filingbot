import asyncio
import logging
import socket

from redis.exceptions import TimeoutError
from sqlalchemy import select
from telegram import Bot
from telegram.error import TelegramError

from core.config import settings
from core.database.models import Filing, User
from core.database.session import AsyncSessionLocal
from core.logging_config import get_logger
from core.redis_client import ack, consume, create_consumer_group, dead_letter
from core.schemas.enums import PipelineStatus, SignalStrength
from workers.notification.message_builder import build_alert_message

base_logger = get_logger("notification")
bot = Bot(token=settings.telegram_bot_token)


async def process_notification(message_id: str, filing_ref: dict[str, str]) -> None:

    async with AsyncSessionLocal() as session:
        stmt = select(Filing).where(
            Filing.accession_number == filing_ref["accession_number"]
        )
        result = (await session.execute(stmt)).scalar_one()
        log = logging.LoggerAdapter(
            base_logger, extra={"correlation_id": result.accession_number}
        )
        if result.signal_strength in (SignalStrength.HIGH, SignalStrength.MEDIUM):
            try:
                message = build_alert_message(result)
                stmt = select(User.telegram_chat_id,User.alerts_all,User.watchlist)
                users = (await session.execute(stmt)).all()

                for users_chat_id,users_alert_all,users_watchlist in users:
                    if not users_alert_all and result.issuer_ticker.upper() not in users_watchlist:
                        continue

                    try:
                        await bot.send_message(chat_id=users_chat_id, text=message)

                    except TelegramError as error:
                        log.error(
                            f"skipping notification of chat id:{users_chat_id} due to {error}"
                        )
                        continue

                result.pipeline_status = PipelineStatus.NOTIFIED
                await session.commit()

            except (TypeError, AttributeError) as e:
                await dead_letter(
                    message=filing_ref["accession_number"],
                    error=str(e),
                    stream="filing.classified",
                    retries=1,
                )
                log.exception("notification failed, sending to dead letter")
                await session.rollback()

        else:
            result.pipeline_status = (
                PipelineStatus.SKIPPED
            )  # if signal is low,noise skip notifying
            await session.commit()

        await ack("filing.classified", "notification_group", message_id)


async def classified_filings_consumer():
    await create_consumer_group("filing.classified", "notification_group")
    await bot.initialize()

    while True:
        try:
            response = await consume(
                groupname="notification_group",
                consumername=socket.gethostname(),
                stream="filing.classified",
                block=4000,
            )
            if not response:
                continue
        except TimeoutError:
            continue

        messages = response[0][1]
        for message_id, fields in messages:
            await process_notification(message_id, fields)


if __name__ == "__main__":
    asyncio.run(classified_filings_consumer())
