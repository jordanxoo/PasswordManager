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
    # Null while the current user is pending confirmation (no org key yet).
    wrapped_org_key: str | None = None
    member_write: bool


class OrgSettingsRequest(BaseModel):
    member_write: bool


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
    # False while pending confirmation (admin hasn't wrapped the org key yet).
    confirmed: bool = True


class RoleUpdateRequest(BaseModel):
    role: OrgRole


class InvitationCreate(BaseModel):
    email: EmailStr
    role: OrgRole = OrgRole.MEMBER


class InvitationResponse(BaseModel):
    model_config = {"from_attributes": True}
    id: UUID
    email: str
    role: OrgRole
    status: str
    created_at: datetime
    expires_at: datetime


class InvitationLookupResponse(BaseModel):
    org_id: UUID
    org_name: str
    role: OrgRole
    email: str
    status: str
    expired: bool


class AcceptInviteRequest(BaseModel):
    token: str = Field(min_length=1, max_length=128)


class ConfirmMemberRequest(BaseModel):
    wrapped_org_key: str = Field(min_length=1, max_length=8192)


class MemberKey(BaseModel):
    user_id: UUID
    wrapped_org_key: str = Field(min_length=1, max_length=8192)


class RotatedItem(BaseModel):
    id: UUID
    encrypted: str = Field(max_length=100_000)
    iv: str = Field(min_length=16, max_length=16)


class TransferOwnershipRequest(BaseModel):
    user_id: UUID


class CollectionCreate(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    # The new collection's AES key, wrapped with the creator's own public key.
    wrapped_collection_key: str = Field(min_length=1, max_length=8192)


class CollectionResponse(BaseModel):
    model_config = {"from_attributes": True}
    id: UUID
    name: str
    created_at: datetime
    # Caller's wrapped copy of the collection key (unwrap with their private key).
    wrapped_collection_key: str


class CollectionAccessGrant(BaseModel):
    email: EmailStr
    # Collection key wrapped with the target member's public key.
    wrapped_collection_key: str = Field(min_length=1, max_length=8192)


class CollectionMemberResponse(BaseModel):
    model_config = {"from_attributes": True}
    user_id: UUID
    email: str
    created_at: datetime


class RotateKeyRequest(BaseModel):
    # Optionally remove a member as part of the same atomic re-key.
    remove_user_id: UUID | None = None
    # New org key wrapped for every remaining confirmed member (incl. the caller).
    member_keys: list[MemberKey]
    # Every shared entry, re-encrypted with the new org key.
    vault_items: list[RotatedItem]


class PublicKeyResponse(BaseModel):
    user_id: UUID
    email: str
    public_key: str


class UploadKeysRequest(BaseModel):
    public_key: str = Field(min_length=1,max_length=4096)
    encrypted_private_key: str = Field(min_length=1,max_length=8192)
    private_key_iv: str = Field(min_length=1,max_length=64)
