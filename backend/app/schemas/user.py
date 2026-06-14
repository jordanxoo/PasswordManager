from pydantic import BaseModel, EmailStr                                                 
from uuid import UUID
from datetime import datetime
from app.schemas.types import UTCDateTime                                                            
from app.models.enums import Role                                                        

                                                                                        
class UserResponse(BaseModel):
    id: UUID
    email: EmailStr
    role: Role
    is_blocked: bool
    totp_enabled: bool
    created_at: UTCDateTime                                                                 

    model_config = {"from_attributes": True}                                             
                

class UpdateRoleRequest(BaseModel):
    role: Role

                                                                                        
class UpdateBlockRequest(BaseModel):
    is_blocked: bool                                        