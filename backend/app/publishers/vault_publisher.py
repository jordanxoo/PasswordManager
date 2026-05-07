import logging
from datetime import datetime
from app.rabbitmq_client import publish_event


logger = logging.getLogger(__name__)


async def publish_vault_event(action: str, user_id: str, vault_id: str = None):
    message = {
        "action": action,
        "user_id":user_id,
        "vault_id":vault_id,
        "timestamp":datetime.now().isoformat()
    }

    await publish_event(f"vault.{action}",message)
