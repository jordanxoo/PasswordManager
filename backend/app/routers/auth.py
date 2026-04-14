from fastapi import APIRouter,Depends
from app.database import get_db
from sqlalchemy.ext.asyncio import AsyncSession
from app.schemas.auth import RegisterRequest, LoginRequest,LoginResponse
from app.services.auth_service import register_user,login_user
router = APIRouter()


@router.post("/register")
async def register(request: RegisterRequest, db: AsyncSession = Depends(get_db)):

    await register_user(db,request.email,request.password,request.salt)

    return {"message" : "registered successfully"}


@router.post("/login", response_model= LoginResponse)
async def login(request: LoginRequest, db: AsyncSession = Depends(get_db)):
    
    result = await login_user(db,request.email,request.password)
    return result