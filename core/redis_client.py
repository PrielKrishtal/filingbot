import redis.asyncio as aioredis
from redis.exceptions import ResponseError

from core.config import settings
from core.logging_config import get_logger

redis_client = aioredis.from_url(settings.redis_url, decode_responses=True,socket_timeout=10)
base_logger = get_logger("redis_client")


async def publish(stream: str, message: dict) -> None:
    return await redis_client.xadd(stream, message)


async def ack(stream: str, group: str, message_id: str) -> None:
    return await redis_client.xack(stream, group, message_id)


async def consume(
    groupname: str, consumername: str, stream: str, block: int = 0, count: int = 10
) -> list:
    return await redis_client.xreadgroup(
        groupname, consumername, {stream: ">"}, count, block
    )


async def dead_letter(message: str, error: str, stream: str, retries: int = 3) -> None:
    return await redis_client.xadd(
        "filing.dead_letter",
        {
            "original_payload": message,
            "error": error,
            "retries": retries,
            "source_stream": stream,
        },
    )


async def create_consumer_group(stream: str, groupname: str) -> None:
    try:
        await redis_client.xgroup_create(
            name=stream, groupname=groupname, id="$", mkstream=True
        )
        base_logger.debug("consumer group ready")

    except ResponseError as e:
        if "BUSYGROUP" in str(e):
            base_logger.debug("consumer group already exists")

        else:
            raise


async def set_value(key: str, value: str) -> None:
    await redis_client.set(key, value)


async def get_value(key: str) -> str | None:
    return await redis_client.get(key)
