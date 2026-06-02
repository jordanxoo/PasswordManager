from pydantic import BaseModel,Field
from typing import Literal,Optional
from datetime import datetime
from uuid import UUID



class ApiKeyCreateRequest(BaseModel):
    name: str = Field(min_length=1,max_length=50)
    scope: Literal["read","write"]
    expires_at: Optional[datetime] = None


class ApiKeyCreateResponse(BaseModel):
    id: UUID
    name: str  
    scope: str
    key: str
    expires_at: Optional[datetime]
    created_at: datetime


class ApiKeyListItem(BaseModel):
    id: UUID
    name: str
    scope: str
    last_used_at: Optional[datetime]
    expires_at: Optional[datetime]
    created_at: datetime

    model_config = {"from_attributes": True}
