from pydantic import BaseModel,ConfigDict
from datetime import datetime
from uuid import UUID
from typing import Optional
from app.models.enums import Category
class VaultCreate(BaseModel):
    name: str
    url: str
    encrypted: str
    iv: str
    expires_at: Optional[datetime] = None
    category: Optional[Category] = None

class VaultUpdate(BaseModel):
    name: str
    url: str
    encrypted: str
    iv: str
    expires_at: Optional[datetime] = None
    category: Optional[Category] = None
class VaultResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    name: str
    url: str
    encrypted: str
    iv: str
    id: UUID
    created_at: datetime
    updated_at: datetime
    expires_at: Optional[datetime] = None
    category: Optional[Category] = None

class VaultPaginatedResponse(BaseModel):
    items: list[VaultResponse]
    next_cursor: Optional[str] = None
    has_next: bool