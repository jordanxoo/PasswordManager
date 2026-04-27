import sqlalchemy as sa
from sqlalchemy import Column,String,DateTime,ForeignKey,JSON
from sqlalchemy.dialects.postgresql import UUID
from uuid import uuid4
from datetime import datetime
from app.database import Base
import enum


class EventType(enum.Enum):
    LOGIN_SUCCESS = "login_success"
    LOGIN_FAILED = "login_failed"
    ACCOUNT_LOCKED = "account_locked"
    LOGOUT = "logout"
    TOKEN_REFRESH = "token_refresh"
    REGISTER = "register"
    VAULT_READ = "vault_read"
    VAULT_CREATE = "vault_create"
    VAULT_UPDATE = "vault_update"
    VAULT_DELETE =  "vault_delete"


class AuditLog(Base):
    __tablename__ = "audit_log"

    id = Column(UUID(as_uuid=True),primary_key=True,default=uuid4)
    user_id = Column(UUID(as_uuid=True),ForeignKey("users.id"),nullable=True)
    ip_address = Column(String,nullable=True)
    user_agent = Column(String,nullable=True)
    event_type = Column(sa.Enum(EventType),nullable=False)
    event_metadata = Column(JSON,nullable=True)
    created_at = Column(DateTime,default=datetime.now)
