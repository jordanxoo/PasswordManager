from pydantic import BaseModel,ConfigDict
from datetime import datetime
from app.schemas.types import UTCDateTime
from uuid import UUID
from typing import Optional
from app.models.enums import Category
from pydantic import field_validator,Field
import base64
class VaultCreate(BaseModel):
    encrypted: str = Field(max_length=100_000)
    iv: str = Field(max_length=512)
    expires_at: Optional[UTCDateTime] = None
    category: Optional[Category] = None
    # When set, the entry is shared with this organization (encrypted with the
    # org key) instead of being personal.
    org_id: Optional[UUID] = None
    # When set, the entry belongs to a collection (encrypted with the collection key).
    collection_id: Optional[UUID] = None

    @field_validator("iv")
    @classmethod
    def validate_iv(cls,v):
        if len(v) != 16:
            raise ValueError("IV must be 16 characters (12 bytes base64)")
        
        try:
            base64.b64decode(v,validate=True)

        except Exception:
            raise ValueError("IV must be valid base64")
        
        return v

class VaultUpdate(BaseModel):
    encrypted: str
    iv: str
    expires_at: Optional[UTCDateTime] = None
    category: Optional[Category] = None

    @field_validator("iv")
    @classmethod
    def validate_iv(cls,v):
        if len(v) != 16:
            raise ValueError("IV must be 16 characters (12 bytes base64)")
        
        try:
            base64.b64decode(v,validate=True)

        except Exception:
            raise ValueError("IV must be valid base64")
        
        return v


class VaultResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    encrypted: str
    iv: str
    id: UUID
    created_at: UTCDateTime
    updated_at: UTCDateTime
    expires_at: Optional[UTCDateTime] = None
    category: Optional[Category] = None
    pinned: bool = False
    org_id: Optional[UUID] = None
    collection_id: Optional[UUID] = None

class VaultPinRequest(BaseModel):
    pinned: bool

class VaultPaginatedResponse(BaseModel):
    items: list[VaultResponse]
    next_cursor: Optional[str] = None
    has_next: bool


class VaultExportResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    version: int = 1
    exported_at: UTCDateTime
    items: list[VaultResponse]

class VaultImportRequest(BaseModel):
    items: list[VaultCreate]
    
    @field_validator("items")
    @classmethod
    def limit(cls,v):
        if len(v) > 1000:
            raise ValueError("Cannot import more than 1000 items at once")
        return v
    

class VaultHistoryResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    vault_id: UUID
    encrypted: str
    iv: str
    changed_at: UTCDateTime
    