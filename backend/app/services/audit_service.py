from app.models.enums import EventType
import logging
from app.schemas.audit import AuditLogFilter
from sqlalchemy import select,func
from datetime import datetime,timedelta
from app.models.models import AuditLog
from fastapi import HTTPException
import json
from app.publishers.audit_publisher import publish_audit_event
logger = logging.getLogger(__name__)


async def log_event(db
                    ,event_type : EventType
                    ,ip_address
                    ,user_agent
                    ,user_id = None
                      ,metadata = None
                      ,org_id = None):

    audit_log = AuditLog(
        user_id = user_id,
        org_id = org_id,
        ip_address = ip_address,
        user_agent = user_agent,
        event_type = event_type,
        event_metadata = metadata
    )

    try:
        db.add(audit_log)
        await db.commit()
        await publish_audit_event(
            event_type.value,
            ip_address,
            user_agent,
            user_id,
            metadata
        )

    except Exception as e:
        logger.error("Error saving auditLog for user logging")


    
_VAULT_EVENTS = [EventType.VAULT_READ, EventType.VAULT_CREATE,
                 EventType.VAULT_UPDATE, EventType.VAULT_DELETE]


async def get_org_audit(db, org_id, limit=50, offset=0, collection_id=None):
    """Audit feed for one organization: who did what, newest first.
    `collection_id` filters: a UUID -> that collection's events; "general" ->
    org-wide shared-item events (no collection); None -> everything."""
    from app.models.models import User
    query = (
        select(AuditLog, User.email)
        .join(User, User.id == AuditLog.user_id, isouter=True)
        .where(AuditLog.org_id == org_id)
    )
    # event_metadata is a generic JSON column, so reach into it with the raw
    # Postgres ->> operator (text extraction) rather than JSONB's .astext.
    coll_text = AuditLog.event_metadata.op("->>")("collection_id")
    if collection_id == "general":
        query = query.where(coll_text.is_(None), AuditLog.event_type.in_(_VAULT_EVENTS))
    elif collection_id:
        query = query.where(coll_text == str(collection_id))

    result = await db.execute(
        query.order_by(AuditLog.created_at.desc()).limit(limit).offset(offset))
    return result.all()


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
    

async def get_audit_stats(db,redis):

    cached = await redis.get("audit:stats")
    if cached:
        return json.loads(cached)
    

    try:
        total_events = await db.execute(select(func.count(AuditLog.id)))
        failed_logins_24 = await db.execute(select(func.count(AuditLog.id)).where(AuditLog.event_type == EventType.LOGIN_FAILED).where(AuditLog.created_at >= datetime.now() - timedelta(hours=24)))
        locked_acoounts_24 = await db.execute(select(func.count(AuditLog.id)).where(AuditLog.event_type == EventType.ACCOUNT_LOCKED).where(AuditLog.created_at >= datetime.now() - timedelta(hours=24)))
        unique_ips = await db.execute(select(func.count(AuditLog.ip_address.distinct())))

        total = total_events.scalar()
        failed = failed_logins_24.scalar()
        locked = locked_acoounts_24.scalar()
        ips = unique_ips.scalar()

        result =  {
            "total_events": total,
            "failed_logins_24": failed,
            "locked_accounts_24": locked,
            "unique_ips": ips
        }
        await redis.setex("audit:stats",60,json.dumps(result))
        return result

    except Exception as e:
        logger.error("Error fetching audit stats: %s",e)
        raise HTTPException(status_code=500,detail="Internal Server Error")



