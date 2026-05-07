import logging
from datetime import datetime
from app.rabbitmq_client import publish_event

logger = logging.getLogger(__name__)


async def publish_security_alert(event_type: str, email: str, ip:str, user_id = None):
    message = {
        "event" : event_type,
        "email" : email,
        "ip" : ip,
        "user_id": user_id,
        "timestamp": datetime.now().isoformat()
    }

    await publish_event(f"security.{event_type}",message)


async def check_and_publish_suspicious_login(redis, email: str, ip: str, user_id: str):
    key = f"known_ip:{user_id}:{ip}"
    known = await redis.get(key)

    if not known:
        await redis.setex(key,2592000,"1")
        await publish_security_alert("suspicious_login",email,ip,user_id)
        logger.info("Suspicious login detected for user %s from IP %s",user_id,ip)

        