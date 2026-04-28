from app.models.enums import EventType
import logging
from app.schemas.audit import AuditLogFilter
from sqlalchemy import select
from app.models.models import AuditLog

logger = logging.getLogger(__name__)


async def log_event(db
                    ,event_type : EventType
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


    
async def get_audit_logs(db,filters: AuditLogFilter):

    query = select(AuditLog)
    
    if filters.user_id:
        query = query.where(AuditLog.user_id == filters.user_id)

    if filters.event_type:
        query = query.where(AuditLog.event_type == filters.event_type)

    if filters.date_from:
        query = query.where(AuditLog.created_at >= filters.date_from)

    if filters.date_to:
        query = query.where(AuditLog.created_at <= filters.date_to)

    if filters.ip_address:
        query = query.where(AuditLog.ip_address == filters.ip_address)

    query = query.order_by(AuditLog.created_at.desc()).limit(filters.limit).offset(filters.offset)

    result = await db.execute(query)
    return result.scalars().all()
    