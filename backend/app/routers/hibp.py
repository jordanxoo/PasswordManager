from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.database import get_db
from app.dependencies import get_current_user
from app.redis_client import get_redis
from app.services.hibp_service import check_rate_limit, check_password_range,check_email_breach
from app.services.audit_service import log_event
from app.models.models import User
from app.models.enums import EventType

router = APIRouter()

@router.get("/password")
async def hibp_password(
    request: Request,
    hash_prefix: str = Query(..., min_length=5, max_length=5),
    db: AsyncSession = Depends(get_db),
    redis=Depends(get_redis),
    user_id: str = Depends(get_current_user)
):
    await check_rate_limit(redis, user_id)
    result = await check_password_range(hash_prefix, redis)
    await log_event(db, EventType.HIBP_PASSWORD_CHECK, request.client.host,
                    request.headers.get("user-agent"), user_id)
    return result


@router.get("/email")
async def hibp_email(
    request: Request,
    db: AsyncSession = Depends(get_db),
    redis=Depends(get_redis),
    user_id: str = Depends(get_current_user)
):
    await check_rate_limit(redis, user_id)
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    breaches = await check_email_breach(user.email)
    await log_event(db, EventType.HIBP_EMAIL_CHECK, request.client.host,
                    request.headers.get("user-agent"), user_id)
    return breaches

