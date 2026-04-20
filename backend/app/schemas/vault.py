from pydantic import BaseModel,ConfigDict
from datetime import datetime
from uuid import UUID


class VaultCreate(BaseModel):
    name: str
    url: str
    encrypted: str
    iv: str

class VaultUpdate(BaseModel):
    name: str
    url: str
    encrypted: str
    iv: str

class VaultResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    name: str
    url: str
    encrypted: str
    iv: str
    id: UUID
    created_at: datetime
    updated_at: datetime