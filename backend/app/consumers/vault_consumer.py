import aio_pika
import json
import logging
import asyncio 
from app.config import settings


logger = logging.getLogger(__name__)

async def consume_vault_events():
    connection = await aio_pika.connect_robust(settings.RABBITMQ_URL)
    channel = await connection.channel()
    await channel.set_qos(prefetch_count=1)
    queue = await  channel.get_queue("vault.sync")

    async def on_message(message: aio_pika.IncomingMessage):
        async with message.process():
            data = json.loads(message.body)
            logger.info("VAULT EVENT | action=%s user_id=%s vault_id=%s",
                          data.get("action"), data.get("user_id"), data.get("vault_id"))   
  
    await queue.consume(on_message)                                                      
    logger.info("Vault consumer started")
    await asyncio.Future()                    