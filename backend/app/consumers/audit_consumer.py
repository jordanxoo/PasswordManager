import aio_pika
import json
import logging
import asyncio
from app.config import settings

logger = logging.getLogger(__name__)

async def consume_audit_events():
    connection = await aio_pika.connect_robust(settings.RABBITMQ_URL)
    channel = await connection.channel()
    await channel.set_qos(prefetch_count=1)
    queue = await channel.get_queue("audit.events")

    async def on_message(message: aio_pika.IncomingMessage):
        async with message.process():
            data = json.loads(message.body)
            logger.info("AUDIT EVENT | event=%s user_id=%s ip=%s timestamp=%s",
                          data.get("event"), data.get("user_id"),
                          data.get("ip"), data.get("timestamp"))                           
   
    await queue.consume(on_message)                                                      
    logger.info("Audit consumer started")
    await asyncio.Future()
