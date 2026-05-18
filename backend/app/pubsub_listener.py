import asyncio
import json
from app.redis_client import create_redis_client
from app.websocket_manager import manager


async def redis_pubsub_listener():
    redis = create_redis_client()
    pubsub = redis.pubsub()
    await pubsub.psubscribe("notifications:*")

    try:
        async for message in pubsub.listen():
            if message["type"] != "pmessage":
                continue

            channel = message["channel"]
            user_id = channel.split(":")[-1]
            data = json.loads(message["data"])
            await manager.send(user_id,data)

    finally:
        await pubsub.punsubscribe()
        await redis.aclose()