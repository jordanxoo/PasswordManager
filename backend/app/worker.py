import asyncio 
import logging
from app.consumers.security_consumer import consume_security_alerts
from app.consumers.audit_consumer import consume_audit_events
from app.consumers.notification_consumer import consume_notifications
from app.consumers.vault_consumer import consume_vault_events


logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def main():
    logger.info("Worker starting...")
    await asyncio.gather(
        consume_security_alerts(),
        consume_audit_events(),
        consume_notifications(),
        consume_vault_events()
    )


if __name__ == "__main__":
    asyncio.run(main())
