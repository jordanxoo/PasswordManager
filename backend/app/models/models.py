from sqlalchemy import Column,String,DateTime,ForeignKey,JSON, Boolean,UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from uuid import uuid4
from datetime import datetime
from app.database import Base
from app.models.enums import EventType,Role,Category,OrgRole
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
    # Asymmetric keypair for organization secret sharing (zero-knowledge).
    # public_key: SPKI base64, stored in plaintext. private key is encrypted
    # client-side with the user's AES encryption key — server only sees ciphertext.
    public_key = Column(String,nullable=True)
    encrypted_private_key = Column(String,nullable=True)
    private_key_iv = Column(String,nullable=True)

class Vault(Base):
    __tablename__ = "vaults"

    id = Column(UUID(as_uuid=True),primary_key=True,default=uuid4)
    user_id = Column(UUID(as_uuid=True),ForeignKey("users.id"),nullable=False)
    # When set, the entry is org-shared (encrypted with the org key) instead of
    # personal. user_id then identifies the creator. Personal entry => org_id NULL.
    org_id = Column(UUID(as_uuid=True),ForeignKey("organizations.id"),nullable=True)
    encrypted = Column(String,nullable=False)
    iv = Column(String,nullable=False)
    created_at = Column(DateTime,default= datetime.now)
    updated_at = Column(DateTime,default=datetime.now)
    expires_at = Column(DateTime,nullable=True)
    category = Column(sa.Enum(Category),nullable=True)
    is_deleted = Column(Boolean,default=False,nullable=False)
    pinned = Column(Boolean,default=False,nullable=False,server_default=sa.false())


class Organization(Base):
    __tablename__ = "organizations"

    id = Column(UUID(as_uuid=True),primary_key=True,default=uuid4)
    name = Column(String,nullable=False)
    owner_id = Column(UUID(as_uuid=True),ForeignKey("users.id"),nullable=False)
    created_at = Column(DateTime,default=datetime.now)
    # When True, any member may add/edit/delete shared entries; when False,
    # only admins/owner can write and plain members are read-only. Owner-toggled.
    member_write = Column(Boolean,nullable=False,default=True,server_default=sa.true())


class OrganizationMembership(Base):
    __tablename__ = "organization_memberships"
    __table_args__ = (UniqueConstraint("org_id","user_id",name="uq_org_member"),)

    id = Column(UUID(as_uuid=True),primary_key=True,default=uuid4)
    org_id = Column(UUID(as_uuid=True),ForeignKey("organizations.id"),nullable=False)
    user_id = Column(UUID(as_uuid=True),ForeignKey("users.id"),nullable=False)
    role = Column(sa.Enum(OrgRole),nullable=False,default=OrgRole.MEMBER)
    # The org's AES key, wrapped (RSA-OAEP) with this member's public key.
    # Each member unwraps it with their own private key — server never sees it.
    # NULL while a member is "pending confirmation": they accepted an invite but
    # an admin has not yet wrapped the org key for them.
    wrapped_org_key = Column(String,nullable=True)
    created_at = Column(DateTime,default=datetime.now)


class OrganizationInvitation(Base):
    __tablename__ = "organization_invitations"

    id = Column(UUID(as_uuid=True),primary_key=True,default=uuid4)
    org_id = Column(UUID(as_uuid=True),ForeignKey("organizations.id"),nullable=False)
    email = Column(String,nullable=False)
    role = Column(sa.Enum(OrgRole),nullable=False,default=OrgRole.MEMBER)
    # sha256 of the random invite token; the token itself only ever lives in the
    # emailed link, never in the database.
    token_hash = Column(String,nullable=False,index=True)
    status = Column(String,nullable=False,default="pending")  # pending|accepted|revoked
    invited_by = Column(UUID(as_uuid=True),ForeignKey("users.id"),nullable=False)
    created_at = Column(DateTime,default=datetime.now)
    expires_at = Column(DateTime,nullable=False)

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



