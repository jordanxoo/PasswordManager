from pydantic import BaseModel,EmailStr,Field
from datetime import datetime
from uuid import UUID
from app.models.enums import OrgRole


class OrganizationCreate(BaseModel):
    name: str = Field(min_length=1,max_length=100)
    # The org's AES key, wrapped with the creator's own public key.
    wrapped_org_key: str = Field(min_length=1,max_length=8192)


class OrganizationResponse(BaseModel):
    model_config = {"from_attributes": True}
    id: UUID
    name: str
    created_at: datetime
    # Current user's role + their wrapped copy of the org key (so they can
    # unwrap it with their private key). Populated per-request, not from the
    # Organization row itself.
    role: OrgRole
    wrapped_org_key: str


class MemberAddRequest(BaseModel):
    email: EmailStr
    role: OrgRole = OrgRole.MEMBER
    # The org key wrapped with the new member's public key (computed client-side
    # by the inviter after fetching that user's public key).
    wrapped_org_key: str = Field(min_length=1,max_length=8192)


class MemberResponse(BaseModel):
    model_config = {"from_attributes": True}
    user_id: UUID
    email: str
    role: OrgRole
    created_at: datetime


class RoleUpdateRequest(BaseModel):
    role: OrgRole


class PublicKeyResponse(BaseModel):
    user_id: UUID
    email: str
    public_key: str


class UploadKeysRequest(BaseModel):
    public_key: str = Field(min_length=1,max_length=4096)
    encrypted_private_key: str = Field(min_length=1,max_length=8192)
    private_key_iv: str = Field(min_length=1,max_length=64)
