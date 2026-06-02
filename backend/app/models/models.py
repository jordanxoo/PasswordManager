from sqlalchemy import Column,String,DateTime,ForeignKey,JSON, Boolean
from sqlalchemy.dialects.postgresql import UUID
from uuid import uuid4
from datetime import datetime
from app.database import Base
from app.models.enums import EventType,Role,Category
import sqlalchemy as sa


class User(Base):
    __tablename__ = "users"

    id = Column(UUID(as_uuid=True),primary_key=True,default=uuid4)
    email = Column(String,unique=True,nullable=False)
    password = Column(String,nullable=False)
    salt = Column(String,nullable=False)
    created_at = Column(DateTime,default=datetime.now)
    totp_secret = Column(String,nullable=True)
    totp_enabled = Column(Boolean,nullable=False,default=False)
    role = Column(sa.Enum(Role),nullable=False,default=Role.USER)
    is_blocked = Column(Boolean,default=False)

class Vault(Base):
    __tablename__ = "vaults"

    id = Column(UUID(as_uuid=True),primary_key=True,default=uuid4)
    user_id = Column(UUID(as_uuid=True),ForeignKey("users.id"),nullable=False)
    name = Column(String,nullable=False)
    url = Column(String, nullable= False)
    encrypted = Column(String,nullable=False)
    iv = Column(String,nullable=False)
    created_at = Column(DateTime,default= datetime.now)
    updated_at = Column(DateTime,default=datetime.now)
    expires_at = Column(DateTime,nullable=True)
    category = Column(sa.Enum(Category),nullable=True)
    is_deleted = Column(Boolean,default=False,nullable=False)

class RefreshToken(Base):
    __tablename__ = "refresh_tokens"

    id = Column(UUID(as_uuid=True),primary_key=True,default=uuid4)
    user_id = Column(UUID(as_uuid=True),ForeignKey("users.id"),nullable=False)
    token = Column(String,nullable=False)
    family_id = Column(String,nullable=False)
    expires_at = Column(DateTime,nullable=False)
    is_used = Column(Boolean,default=False,nullable=False)

class AuditLog(Base):
    __tablename__ = "audit_log"

    id = Column(UUID(as_uuid=True),primary_key=True,default=uuid4)
    user_id = Column(UUID(as_uuid=True),ForeignKey("users.id"),nullable=True)
    ip_address = Column(String,nullable=True)
    user_agent = Column(String,nullable=True)
    event_type = Column(sa.Enum(EventType),nullable=False)
    event_metadata = Column(JSON,nullable=True)
    created_at = Column(DateTime,default=datetime.now)

class VaultHistory(Base):
    __tablename__ = "vault_history"
    id = Column(UUID(as_uuid=True),primary_key=True,default=uuid4)
    vault_id = Column(UUID(as_uuid=True),ForeignKey("vaults.id"),nullable=False)
    name = Column(String,nullable=False)
    url = Column(String,nullable=False)
    encrypted = Column(String,nullable=False)
    iv = Column(String,nullable=False)
    changed_at = Column(DateTime,default=datetime.now)

class RecoveryCode(Base):
    __tablename__ = "recovery_codes"
    id = Column(UUID(as_uuid=True),primary_key=True,default=uuid4)
    user_id = Column(UUID,ForeignKey("users.id"),nullable=False)
    code_hash = Column(String,nullable=False)
    is_used = Column(Boolean,default=False,nullable=False)
    used_at = Column(DateTime,default=datetime.now)
    

class ApiKey(Base):
    __tablename__ = "api_keys"
    id = Column(UUID(as_uuid=True),primary_key=True,default=uuid4)
    user_id = Column(UUID(as_uuid=True),ForeignKey("users.id"), nullable= False)
    key_hash = Column(String,nullable=False,unique=True)
    name = Column(String(50),nullable=False)
    scope = Column(String(10),nullable=False)
    last_used_at = Column(DateTime,nullable=True)
    expires_at = Column(DateTime,nullable=True)
    created_at = Column(DateTime,default=datetime.now)



