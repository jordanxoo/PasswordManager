from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel

from app.models.enums import EventType


class AuditLogResponse(BaseModel):
    id: UUID
    user_id: Optional[UUID]
    event_type: EventType
    ip_address: Optional[str]
    user_agent: Optional[str]
    event_metadata: Optional[dict]
    created_at: Optional[datetime]

    model_config = {"from_attributes": True}


class AuditLogFilter(BaseModel):
    user_id: Optional[UUID] = None
    event_type: Optional[EventType] = None
    date_from: Optional[datetime] = None
    date_to: Optional[datetime] = None
    ip_address: Optional[str] = None
    limit: int = 50
    offset: int = 0

class AuditLogStats(BaseModel):
    total_events: int
    failed_logins_24: int
    locked_accounts_24: int
    unique_ips: int
