import logging
from datetime import datetime
from app.rabbitmq_client import publish_event


logger = logging.getLogger(__name__)


async def publish_audit_event(event_type:str, ip:str, 
                              user_agent:str, user_id = None,
                              metadata = None):
    message = {
        "event":event_type,
        "ip":ip,
        "user_agent":user_agent,
        "user_id":user_id,
        "metadata":metadata,
        "timestamp":datetime.now().isoformat()
    }

    await publish_event(f"audit.{event_type}",message)
