from sqlalchemy import Column,String,DateTime,ForeignKey,JSON
from sqlalchemy.dialects.postgresql import UUID
from uuid import uuid4
from datetime import datetime
from app.database import Base
from app.models.enums import EventType
import sqlalchemy as sa


class User(Base):
    __tablename__ = "users"

    id = Column(UUID(as_uuid=True),primary_key=True,default=uuid4)
    email = Column(String,unique=True,nullable=False)
    password = Column(String,nullable=False)
    salt = Column(String,nullable=False)
    created_at = Column(DateTime,default=datetime.now)

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

class RefreshToken(Base):
    __tablename__ = "refresh_tokens"

    id = Column(UUID(as_uuid=True),primary_key=True,default=uuid4)
    user_id = Column(UUID(as_uuid=True),ForeignKey("users.id"),nullable=False)
    token = Column(String,nullable=False)
    expires_at = Column(DateTime,nullable=False)

class AuditLog(Base):
    __tablename__ = "audit_log"

    id = Column(UUID(as_uuid=True),primary_key=True,default=uuid4)
    user_id = Column(UUID(as_uuid=True),ForeignKey("users.id"),nullable=True)
    ip_address = Column(String,nullable=True)
    user_agent = Column(String,nullable=True)
    event_type = Column(sa.Enum(EventType),nullable=False)
    event_metadata = Column(JSON,nullable=True)
    created_at = Column(DateTime,default=datetime.now)
