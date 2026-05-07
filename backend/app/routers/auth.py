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

router = APIRouter()


@router.post("/register")
async def register(data: RegisterRequest, 
                   request: Request,
                   db: AsyncSession = Depends(get_db)):

    await register_user(db,data.email,data.password,data.salt)
    await log_event(db,EventType.REGISTER,request.client.host,
                    request.headers.get("user-agent"))
    
    return {"message" : "registered successfully"}


@router.post("/login", response_model= LoginResponse)
async def login(data: LoginRequest,
                response: Response,
                request: Request,
                db: AsyncSession = Depends(get_db),
                redis = Depends(get_redis)):
    try:
        result = await login_user(db,redis,data.email,data.password)
      
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
    await log_event(db,EventType.TOKEN_REFRESH,request.client.host,request.headers.get("user-agent"))
    return result

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
