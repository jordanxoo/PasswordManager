from fastapi import APIRouter, Depends
from app.database import get_db
from app.dependencies import get_current_user
from sqlalchemy.ext.asyncio import AsyncSession 
from app.schemas.audit import AuditLogFilter, AuditLogResponse,AuditLogStats
from app.services.audit_service import get_audit_logs,get_audit_stats
from app.redis_client import get_redis


router = APIRouter()

@router.get("/audit-log",response_model=list[AuditLogResponse])
async def audit_endpoint(filters: AuditLogFilter = Depends(), 
                         db : AsyncSession = Depends(get_db),
                         user_id: str = Depends(get_current_user)):
    

    result = await get_audit_logs(db,filters)

    return list(result)

    
@router.get("/stats",response_model=AuditLogStats)
async def audit_log_endpoint(db: AsyncSession = Depends(get_db),
                             user_id: str = Depends(get_current_user),
                             redis = Depends(get_redis)):

    result = await get_audit_stats(db,redis)

    return result