import aio_pika
import json
import logging
import asyncio
import aiosmtplib
from email.mime.text import MIMEText
from app.config import settings

logger = logging.getLogger(__name__)

async def send_email(to: str, subject: str, body: str):
    message = MIMEText(body)
    message["From"] = "noreply@passwordmanager.local"
    message["To"] = to
    message["Subject"] = subject

    await aiosmtplib.send(
        message,
        hostname=settings.MAILHOG_HOST,
        port = settings.MAILHOG_PORT
    )

    logger.info("Email sent to %s | subject: %s",to,subject)


async def consume_notifications():
    connection = await aio_pika.connect_robust(settings.RABBITMQ_URL)
    channel = await connection.channel()
    await channel.set_qos(prefetch_count=1)
    queue = await channel.get_queue("notifications.email")


    async def on_message(message: aio_pika.IncomingMessage):
        async with message.process():
            data = json.loads(message.body)
            await send_email(
                to = data["to"],
                subject=data["subject"],
                body=data["body"]
            )


    await queue.consume(on_message)
    logger.info("Notification consumer started")
    await asyncio.Future()