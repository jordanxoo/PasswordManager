from pydantic import BaseModel,EmailStr,Field,field_validator


class RegisterRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8,max_length=128)
    salt: str = Field(min_length=1,max_length=512)

class LoginRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=1,max_length=128)

class LoginResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    salt: str


class TwoFactorSetupResponse(BaseModel):                                                 
    secret: str
    qr_code: str                                                                         
                                                                                           
   
class TwoFactorVerifyRequest(BaseModel):                                                 
    code: str = Field(min_length=6,max_length=6, pattern=r'^\d{6}$')        


class TwoFactorValidateRequest(BaseModel):
    code: str = Field(min_length=6,max_length=6,pattern=r'^\d{6}$')
