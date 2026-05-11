from pydantic import BaseModel,EmailStr
from datetime import datetime
from uuid import UUID
from app.models.enums import Role,EventType
from typing import Optional

class ProfileResponse(BaseModel):
    model_config = {"from_attributes": True}
    email: str
    created_at: datetime
    totp_enabled: bool
    role: Role

class ChangeEmailRequest(BaseModel):
    new_email: EmailStr
    current_password: str

class ChangePasswordRequest(BaseModel):
    current_password: str
    new_password: str
    new_salt: str

class DeleteAccountRequest(BaseModel):
    current_password: str

class SessionResponse(BaseModel):
    model_config = {"from_attributes": True}
    id: UUID
    expires_at: datetime

class AuditLogResponse(BaseModel):
    model_config = {"from_attributes": True}
    event_type: EventType
    ip_address: Optional[str]
    user_agent: Optional[str]
    created_at: datetime
