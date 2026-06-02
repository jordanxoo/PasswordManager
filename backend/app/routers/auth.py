from fastapi import APIRouter,Depends,HTTPException,Response,Cookie,Request
from app.database import get_db
from sqlalchemy.ext.asyncio import AsyncSession
from app.schemas.auth import RegisterRequest, LoginRequest,LoginResponse
from app.services.auth_service import register_user,login_user,logout,refresh_access_token,get_salt
from app.dependencies import oauth2_scheme
from app.redis_client import get_redis
from app.services.audit_service import log_event
from app.models.enums import EventType
from jose import jwt
from app.config import settings
from app.publishers.security_publisher import publish_security_alert,check_and_publish_suspicious_login
from app.services.auth_service import (                                                  
      register_user, login_user, logout, refresh_access_token,                             
      get_salt, setup_2fa, verify_2fa_setup, disable_2fa, validate_2fa_code
  )                    
from app.services.recovery_service import generate_recovery_codes,get_remaining_count,validate_recovery_code                                                                    
from app.schemas.auth import (
    RegisterRequest, LoginRequest, LoginResponse,                                        
    TwoFactorSetupResponse, TwoFactorVerifyRequest, TwoFactorValidateRequest,RecoveryStatusResponse,RecoveryValidateRequest,RecoveryCodesResponse
)

from app.dependencies import get_current_user
from app.models import User
from sqlalchemy import select
import pyotp
import secrets
from app.models.models import RefreshToken
from datetime import datetime, timedelta

router = APIRouter()


@router.post("/register")
async def register(data: RegisterRequest, 
                   request: Request,
                   db: AsyncSession = Depends(get_db)):

    await register_user(db,data.email,data.password,data.salt)
    await log_event(db,EventType.REGISTER,request.client.host,
                    request.headers.get("user-agent"))
    
    return {"message" : "registered successfully"}


@router.post("/login")
async def login(data: LoginRequest,
                response: Response,
                request: Request,
                db: AsyncSession = Depends(get_db),
                redis = Depends(get_redis)):
    try:
        result = await login_user(db,redis,data.email,data.password)
        if result.get("requires_2fa"):
            response.set_cookie(
                key = "pending_token",
                value=result["pending_token"],
                httponly=True,
                secure=True,
                samesite="lax",
                max_age=300
            )
            return {"requires_2fa": True}
    except HTTPException as e:
        if e.status_code == 401:
            await log_event(db,EventType.LOGIN_FAILED,
                            request.client.host,
                            request.headers.get("user-agent"))
        
        elif e.status_code == 429:
            await log_event(db,EventType.ACCOUNT_LOCKED,request.client.host,request.headers.get("user-agent"))
            await publish_security_alert("account_locked",data.email,request.client.host)
        raise 
        

    
    response.set_cookie(
        key="refresh_token",
        value=result["refresh_token"],
        httponly=True,
        secure=True,
        samesite="lax"
    )
    await log_event(db,EventType.LOGIN_SUCCESS,request.client.host,
                    request.headers.get("user-agent"),user_id=result["user_id"])
    await check_and_publish_suspicious_login(redis, data.email,request.client.host,result["user_id"])
    return LoginResponse(
        access_token=result["access_token"],
        token_type="bearer",
        salt=result["salt"]
    )


@router.post("/refresh")
async def refresh(request: Request,
                   refresh_token: str = Cookie(None),
                   db: AsyncSession = Depends(get_db),
                   redis = Depends(get_redis)):
    if refresh_token is None:
        raise HTTPException(status_code=401,detail="No refresh token")
    

    result =  await refresh_access_token(db,refresh_token,redis)
    Response.set_cookie(
        key="refresh_token",
        value= result["new_refresh_token"],
        httponly=True,
        secure=True,
        samesite="lax"
    )
    await log_event(db,EventType.TOKEN_REFRESH,request.client.host,request.headers.get("user-agent"))
    return {"access_token": result["access_token"]}

@router.post("/logout")
async def logout_endpoint(response: Response, 
                          request: Request,
                          refresh_token: str = Cookie(None),
                          db: AsyncSession = Depends(get_db),
                          access_token: str = Depends(oauth2_scheme),
                          redis = Depends(get_redis)):
    if refresh_token is None:
        raise HTTPException(status_code=401,detail="No refresh token")
    
    result = await logout(db,redis,refresh_token,access_token)

    payload = jwt.decode(access_token,settings.JWT_SECRET,algorithms=["HS256"])
    user_id = payload.get("sub")
    await log_event(db,EventType.LOGOUT,request.client.host,
                    request.headers.get("user-agent"),user_id)
    response.delete_cookie("refresh_token")
    return result

@router.get("/salt")
async def salt_endpoint(email: str,
                        db: AsyncSession = Depends(get_db),
                        redis = Depends(get_redis)):
    salt = await get_salt(db,email,redis)
    return {"salt" : salt}


@router.post("/2fa/setup")
async def setup_2fa_endpoint(db: AsyncSession = Depends(get_db),                         
                            user_id: str = Depends(get_current_user)):
    return await setup_2fa(db, user_id)                                                  
                                                                                        
                                                                                        
@router.post("/2fa/verify")
async def verify_2fa_endpoint(data: TwoFactorVerifyRequest,                              
                                request: Request,           
                                db: AsyncSession = Depends(get_db),                       
                                user_id: str = Depends(get_current_user)):
    result = await verify_2fa_setup(db, user_id, data.code)                              
    await log_event(db, EventType.TWO_FA_ENABLED, request.client.host,
                    request.headers.get("user-agent"), user_id)                                              
    return result                          
                            

                                                                                    
@router.post("/2fa/disable")                                                             
async def disable_2fa_endpoint(data: TwoFactorVerifyRequest,
                                request: Request,                                        
                                db: AsyncSession = Depends(get_db),
                                user_id: str = Depends(get_current_user)):
    result = await disable_2fa(db, user_id, data.code)                                   
    user = (await db.execute(select(User).where(User.id ==
            user_id))).scalar_one_or_none()                                                          
    await log_event(db, EventType.TWO_FA_DISABLED, request.client.host,                  
                    request.headers.get("user-agent"), user_id)
    await publish_security_alert("2fa_disabled", user.email, request.client.host,        
                                user_id)        
    return result                                                           
                                                                                    

@router.post("/2fa/validate")
async def validate_2fa_endpoint(
    response: Response,
    request: Request,
    data: TwoFactorValidateRequest,
    pending_token: str = Cookie(None),
    db: AsyncSession = Depends(get_db),
    redis = Depends(get_redis)):

    if pending_token is None:
        raise HTTPException(status_code=401, detail="No pending token")

    result = await validate_2fa_code(db, redis, pending_token, data.code)

    response.delete_cookie("pending_token")
    response.set_cookie(key="refresh_token", value=result["refresh_token"],
                        httponly=True, secure=True, samesite="lax")
    await log_event(db, EventType.TWO_FA_SUCCESS, request.client.host,
                    request.headers.get("user-agent"), result["user_id"])
    await check_and_publish_suspicious_login(redis, result["email"],
                                            request.client.host, result["user_id"])
    return LoginResponse(access_token=result["access_token"], token_type="bearer",
                        salt=result["salt"])

@router.post("/2fa/recovery/generate", response_model=RecoveryCodesResponse)
async def generate_recovery_codes_endpoint(
    data: TwoFactorVerifyRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
    user_id: str = Depends(get_current_user)):

    user = (await db.execute(select(User).where(User.id == user_id))).scalar_one_or_none()

    if user is None or not user.totp_enabled:
        raise HTTPException(status_code=400, detail="2FA not enabled")

    if not pyotp.TOTP(user.totp_secret).verify(data.code):
        raise HTTPException(status_code=401, detail="Invalid TOTP code")

    codes = await generate_recovery_codes(db, user_id)
    await log_event(db, EventType.RECOVERY_CODES_GENERATED,request.client.host,
                   request.headers.get("user-agent"), user_id)

    return RecoveryCodesResponse(
        codes=codes,
        message="Save these codes — they won't be shown again"
    )


@router.post("/2fa/recovery/validate")
async def validate_recovery_endpoint(
    response: Response,
    request: Request,
    data: RecoveryValidateRequest,
    pending_token: str = Cookie(None),
    db: AsyncSession = Depends(get_db),
    redis = Depends(get_redis)):

    if pending_token is None:
        raise HTTPException(status_code=401, detail="No pending token")

    user_id = await redis.get(f"2fa_pending:{pending_token}")

    if user_id is None:
        raise HTTPException(status_code=401, detail="Invalid or expired token")

    is_valid = await validate_recovery_code(db, user_id, data.code)

    if not is_valid:
        await log_event(db, EventType.RECOVERY_CODE_FAILED, request.client.host,
                        request.headers.get("user-agent"), user_id)
        raise HTTPException(status_code=401, detail="Invalid recovery code")

    user = (await db.execute(select(User).where(User.id == user_id))).scalar_one_or_none()

    if user is None:
        raise HTTPException(status_code=404, detail="User not found")

    await redis.delete(f"2fa_pending:{pending_token}")

    payload = {
        "sub": str(user.id),
        "exp": datetime.now() + timedelta(minutes=15)
    }
    jwt_token = jwt.encode(payload, settings.JWT_SECRET, algorithm="HS256")
    refresh_token = secrets.token_hex(32)
    family_id = secrets.token_hex(16)

    refresh_record = RefreshToken(
        user_id=user.id,
        token=refresh_token,
        family_id=family_id,
        expires_at=datetime.now() + timedelta(days=7),
        is_used=False
    )
    db.add(refresh_record)
    await db.commit()

    await redis.setex(f"refresh:{refresh_token}", 604800, str(user.id))
    db.add(refresh_record)
    await db.commit()
    await redis.setex(f"refresh:{refresh_token}", 604800, str(user.id))
    response.set_cookie(key="refresh_token", value=refresh_token,
                        httponly=True, secure=True, samesite="lax")

    await log_event(db, EventType.RECOVERY_CODES_USED, request.client.host,
                    request.headers.get("user-agent"), str(user.id))

    return LoginResponse(
        access_token=jwt_token,
        token_type="bearer",
        salt=user.salt
    )


@router.get("/2fa/recovery/status", response_model=RecoveryStatusResponse)
async def recovery_status_endpoint(
    db: AsyncSession = Depends(get_db),
    user_id: str = Depends(get_current_user)):

    return await get_remaining_count(db, user_id)