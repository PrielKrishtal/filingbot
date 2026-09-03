import redis.asyncio as aioredis                                                                                                                                                            
from core.config import settings        

redis_client = aioredis.from_url(settings.redis_url)

async def publish(stream: str, message: dict) -> None:
    return await redis_client.xadd(stream, message )

async def ack(stream: str, group:str, message_id: str) -> None:
    return await redis_client.xack(stream,group, message_id)

async def consume(groupname: str, consumername: str, stream: str, block: int = 0, count: int = 10) -> list:
    return await redis_client.xreadgroup(groupname, consumername, {stream: '>'}, count, block)

async def dead_letter(message: str, error:str, stream:str,retries: int = 3) -> None:
    return await redis_client.xadd("filing.dead_letter",{
                "original_payload": message,
                "error": error,
                "retries": retries,
                "source_stream": stream})      



async def set_value(key: str, value: str) -> None:
    await redis_client.set(key, value)

async def get_value(key: str) -> str | None:
    value = await redis_client.get(key)
    return value.decode() if value else None
