import aio_pika
import logging
import json
from aio_pika import ExchangeType,Message,DeliveryMode
from app.config import settings

logger = logging.getLogger(__name__)
_connection = None

async def connect_rabbitmq():
    global _connection
    try:
        _connection = await aio_pika.connect_robust(settings.RABBITMQ_URL)
        logger.info("RabbitMQ connected")
    except Exception as e:
        logger.error("Failed to connect to RabbitMQ: %s",e)
        raise
async def get_channel():
    try:
        _channel = await _connection.channel()
        return _channel
    except Exception as e:
        logger.error("Failed to create a channel: %s",e)
        raise
async def disconnect_rabbitmq():
    if _connection and not _connection.is_closed:
        try:
            await _connection.close()
            logger.info("RabbitMQ disconnected")    
        except Exception as e:
            logger.error("Failed to disconnect RabbitMQ: %s",e)
            

async def setup_rabbitmq():

    channel = await get_channel()

    exchange = await channel.declare_exchange(
        name = "app_events",
        type = ExchangeType.TOPIC,
        durable=True
    )

    security_queue = await channel.declare_queue("security.alerts",durable=True)
    audit_queue = await channel.declare_queue("audit.events",durable=True)
    notification_queue = await channel.declare_queue("notifications.email",durable=True)
    vault_queue = await channel.declare_queue("vault.sync",durable=True)

    await security_queue.bind(exchange,routing_key="security.#")
    await audit_queue.bind(exchange,routing_key="audit.#")
    await notification_queue.bind(exchange,routing_key="notify.#")
    await vault_queue.bind(exchange,routing_key="vault.#")

    await channel.close()

    logger.info("RabbitMQ exchanges and queues configured")




async def publish_event(routing_key: str, message: dict):
    try:
        channel = await get_channel()

        exchange = await channel.get_exchange("app_events")

        body = json.dumps(message).encode()

        await exchange.publish(
            Message(
                body=body,
                delivery_mode=DeliveryMode.PERSISTENT
            ),
            routing_key=routing_key
        )
        await channel.close()

    except Exception as e:
        logger.error("Failed to publish event '%s': '%s'",routing_key,e)


