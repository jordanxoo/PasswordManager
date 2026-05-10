from pydantic import BaseModel,EmailStr


class RegisterRequest(BaseModel):
    email: EmailStr
    password: str
    salt: str

class LoginRequest(BaseModel):
    email: EmailStr
    password: str

class LoginResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    salt: str


class TwoFactorSetupResponse(BaseModel):                                                 
    secret: str
    qr_code: str                                                                         
                                                                                           
   
class TwoFactorVerifyRequest(BaseModel):                                                 
    code: str        


class TwoFactorValidateRequest(BaseModel):
    pending_token: str
    code: str
