from fastapi import APIRouter,Depends,HTTPException,Response,Cookie
from app.database import get_db
from sqlalchemy.ext.asyncio import AsyncSession
from app.schemas.auth import RegisterRequest, LoginRequest,LoginResponse
from app.services.auth_service import register_user,login_user,logout,refresh_access_token,get_salt
from app.dependencies import oauth2_scheme
from app.redis_client import get_redis

router = APIRouter()


@router.post("/register")
async def register(request: RegisterRequest, db: AsyncSession = Depends(get_db)):

    await register_user(db,request.email,request.password,request.salt)

    return {"message" : "registered successfully"}


@router.post("/login", response_model= LoginResponse)
async def login(request: LoginRequest,
                response: Response,
                  db: AsyncSession = Depends(get_db),
                  redis = Depends(get_redis)):
    
    result = await login_user(db,request.email,request.password,redis)
    response.set_cookie(
        key="refresh_token",
        value=result["refresh_token"],
        httponly=True,
        secure=True,
        samesite="lax"
    )

    return LoginResponse(
        access_token=result["access_token"],
        token_type="bearer",
        salt=result["salt"]
    )


@router.post("/refresh")
async def refresh(refresh_token: str = Cookie(None), db: AsyncSession = Depends(get_db)):
    if refresh_token is None:
        raise HTTPException(status_code=401,detail="No refresh token")
    
    return await refresh_access_token(db,refresh_token)



@router.post("/logout")
async def logout_endpoint(response: Response, 
                          refresh_token: str = Cookie(None),
                          db: AsyncSession = Depends(get_db),
                          access_token: str = Depends(oauth2_scheme),
                          redis = Depends(get_redis)):
    if refresh_token is None:
        raise HTTPException(status_code=401,detail="No refresh token")
    
    result = await logout(db,redis,refresh_token,access_token)
    response.delete_cookie("refresh_token")
    return result

@router.get("/salt")
async def salt_endpoint(email: str,
                        db: AsyncSession = Depends(get_db),
                        redis = Depends(get_redis)):
    salt = await get_salt(db,email,redis)
    return {"salt" : salt}
