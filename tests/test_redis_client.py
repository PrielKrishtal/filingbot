import pytest
import pytest_asyncio
import redis.asyncio as aioredis
from redis.exceptions import RedisError

from core import redis_client as redis_module
from core.config import settings

TEST_CHAT_ID = 999999
TEST_KEY = f"ratelimit:{TEST_CHAT_ID}"


@pytest_asyncio.fixture
async def redis(monkeypatch):
    client = aioredis.from_url(
        settings.redis_url, decode_responses=True, socket_connect_timeout=2
    )
    try:
        await client.ping()
    except RedisError:
        await client.aclose()
        pytest.skip("Redis not reachable")

    monkeypatch.setattr(redis_module, "redis_client", client)
    await client.delete(TEST_KEY)
    yield client
    await client.delete(TEST_KEY)
    await client.aclose()


async def test_count_increases_by_one_per_call(redis):
    over_limit = redis_module.MAX_COMMANDS_PER_WINDOW + 1

    for expected_count in range(1, over_limit + 1):
        assert await redis_module.count_command(TEST_CHAT_ID) == expected_count


async def test_first_call_sets_ttl_within_window(redis):
    await redis_module.count_command(TEST_CHAT_ID)

    ttl = await redis.ttl(TEST_KEY)

    assert 0 < ttl <= redis_module.RATE_LIMIT_WINDOW_SECONDS


async def test_later_calls_do_not_reset_ttl(redis):
    await redis_module.count_command(TEST_CHAT_ID)
    await redis.expire(TEST_KEY, 30)

    await redis_module.count_command(TEST_CHAT_ID)

    assert 0 < await redis.ttl(TEST_KEY) <= 30


async def test_redis_error_fails_open_with_zero_count(monkeypatch):
    def broken_pipeline(*args, **kwargs):
        raise RedisError("redis is down")

    monkeypatch.setattr(redis_module.redis_client, "pipeline", broken_pipeline)

    assert await redis_module.count_command(TEST_CHAT_ID) == 0
