from app.models.enums import EventType,AuditLog
import logging

logger = logging.getLogger(__name__)


async def log_event(db
                    ,event_type
                    ,ip_address
                    ,user_agent
                    ,user_id = None
                      ,metadata = None):
    
    audit_log = AuditLog(
        user_id = user_id,
        ip_address = ip_address,
        user_agent = user_agent,
        event_type = event_type,
        event_metadata = metadata
    ) 

    try:
        db.add(audit_log)
        await db.commit()

    except Exception as e:
        logger.error("Error saving auditLog for user logging")


    