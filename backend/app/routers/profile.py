from fastapi import APIRouter,Depends,Request,Cookie
from sqlalchemy.ext.asyncio import AsyncSession
from app.database import get_db
from app.dependencies import get_current_user
from app.schemas.profile import (
    ProfileResponse, ChangeEmailRequest, ChangePasswordRequest,
      DeleteAccountRequest, SessionResponse, AuditLogResponse
  )
from app.services import profile_service
from app.services.audit_service import log_event
from app.models.enums import EventType
from uuid import UUID
from typing import Optional


router = APIRouter()

@router.get("/", response_model=ProfileResponse)
async def get_profile(
    db: AsyncSession = Depends(get_db),
    user_id: str = Depends(get_current_user)
):
    return await profile_service.get_profile(db, user_id)

@router.put("/email")
async def change_email(
    data: ChangeEmailRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
    user_id: str = Depends(get_current_user)
):
    await profile_service.change_email(db, user_id, data.new_email,
data.current_password)
    await log_event(db, EventType.EMAIL_CHANGED, request.client.host,
                    request.headers.get("user-agent"), user_id)
    return {"message": "Email updated"}

@router.put("/password")
async def change_password(
    data: ChangePasswordRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
    user_id: str = Depends(get_current_user)
):
    await profile_service.change_password(db, user_id, data.current_password,
                                        data.new_password, data.new_salt)
    await log_event(db, EventType.PASSWORD_CHANGED, request.client.host,
                    request.headers.get("user-agent"), user_id)
    return {"message": "Password updated. Please log in again."}

@router.delete("/")
async def delete_account(
    data: DeleteAccountRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
    user_id: str = Depends(get_current_user)
):
    await log_event(db, EventType.ACCOUNT_DELETED, request.client.host,
                    request.headers.get("user-agent"), user_id)
    await profile_service.delete_account(db, user_id, data.current_password)
    return {"message": "Account deleted"}

@router.get("/sessions", response_model=list[SessionResponse])
async def get_sessions(
    db: AsyncSession = Depends(get_db),
    user_id: str = Depends(get_current_user)
):
    return await profile_service.get_sessions(db, user_id)

@router.delete("/sessions/{session_id}")
async def revoke_session(
    session_id: UUID,
    request: Request,
    db: AsyncSession = Depends(get_db),
    user_id: str = Depends(get_current_user)
):
    await profile_service.revoke_session(db, user_id, session_id)
    await log_event(db, EventType.SESSION_REVOKED, request.client.host,
                    request.headers.get("user-agent"), user_id)
    return {"message": "Session revoked"}

@router.delete("/sessions")
async def revoke_all_sessions(
    request: Request,
    refresh_token: Optional[str] = Cookie(None),
    db: AsyncSession = Depends(get_db),
    user_id: str = Depends(get_current_user)
):
    await profile_service.revoke_all_sessions(db, user_id, refresh_token)
    await log_event(db, EventType.SESSION_REVOKED, request.client.host,
                    request.headers.get("user-agent"), user_id)
    return {"message": "All other sessions revoked"}

@router.get("/audit", response_model=list[AuditLogResponse])
async def get_audit(
    db: AsyncSession = Depends(get_db),
    user_id: str = Depends(get_current_user)
):
    return await profile_service.get_audit_log(db, user_id)

