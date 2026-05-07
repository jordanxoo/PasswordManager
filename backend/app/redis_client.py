import redis.asyncio as ioredis
from app.config import settings


async def get_redis():
    client = ioredis.from_url(
        settings.REDIS_URL,
        encoding = "utf-8",
        decode_responses = True
    )

    try:
        yield client

    finally:
        await client.aclose()


