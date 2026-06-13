from pydantic import BaseModel,EmailStr,Field,field_validator


class RegisterRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8,max_length=128)
    salt: str = Field(min_length=1,max_length=512)
    # Optional asymmetric keypair generated client-side at registration so the
    # account can take part in organization sharing from the start. Legacy
    # clients may omit them; the keypair is then backfilled on first login.
    public_key: str | None = Field(default=None,max_length=4096)
    encrypted_private_key: str | None = Field(default=None,max_length=8192)
    private_key_iv: str | None = Field(default=None,max_length=64)

class LoginRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=1,max_length=128)

class LoginResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    salt: str
    # Wrapped keypair, returned so the client can unwrap the private key into
    # memory. Null for legacy accounts that have not generated a keypair yet.
    public_key: str | None = None
    encrypted_private_key: str | None = None
    private_key_iv: str | None = None


class TwoFactorSetupResponse(BaseModel):                                                 
    secret: str
    qr_code: str                                                                         
                                                                                           
   
class TwoFactorVerifyRequest(BaseModel):                                                 
    code: str = Field(min_length=6,max_length=6, pattern=r'^\d{6}$')        


class TwoFactorValidateRequest(BaseModel):
    code: str = Field(min_length=6,max_length=6,pattern=r'^\d{6}$')

class TwoFactorVerifyResponse(BaseModel):
    message: str
    recovery_codes: list[str]

class RecoveryCodesResponse(BaseModel):
    codes: list[str]
    message: str

class RecoveryValidateRequest(BaseModel):
    code: str = Field(min_length=9, max_length=9,
    pattern=r'^[a-z0-9]{4}-[a-z0-9]{4}$')

class RecoveryStatusResponse(BaseModel):
    remaining: int
    total: int