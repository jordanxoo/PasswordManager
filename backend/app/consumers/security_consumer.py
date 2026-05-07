import aio_pika
import json
import logging
import asyncio
from app.config import settings

logger = logging.getLogger(__name__)


async def consume_security_alerts():
    connection = await aio_pika.connect_robust(settings.RABBITMQ_URL)
    channel = await connection.channel()
    await channel.set_qos(prefetch_count=1)
    queue = await channel.get_queue("security.alerts")


    async def on_message(message: aio_pika.IncomingMessage):
        async with message.process():
            data = json.loads(message.body)
            logger.warning("SECURITY ALERT | event=%s email=%s ip=%s user_id=%s",
                             data.get("event"), data.get("email"),                         
                             data.get("ip"), data.get("user_id"))


    await queue.consume(on_message)
    logger.info("Security consumer started")
    await asyncio.Future()


    