import asyncio 
import logging
from app.consumers.security_consumer import consume_security_alerts
from app.consumers.audit_consumer import consume_audit_events
from app.consumers.notification_consumer import consume_notifications
from app.consumers.vault_consumer import consume_vault_events
from app.consumers.expiry_consumer import check_expiring_passwords
from app.rabbitmq_client import connect_rabbitmq, setup_rabbitmq
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def main():
    logger.info("Worker starting...")
    await connect_rabbitmq()
    await setup_rabbitmq()
    await asyncio.gather(
        consume_security_alerts(),
        consume_audit_events(),
        consume_notifications(),
        consume_vault_events(),
        check_expiring_passwords()
    )


if __name__ == "__main__":
    asyncio.run(main())
