from fastapi import APIRouter,Depends,Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.database import get_db
from app.dependencies import get_current_user
from app.services.hibp_service import check_email_breach,check_password_range
from app.models.models import User


router = APIRouter()

@router.get("/password")
async def hibp_password(
    hash_prefix: str = Query(...,min_length=5,max_length=5),
    user_id: str = Depends(get_current_user)
):
    return await check_password_range(hash_prefix)


@router.get("/email")
async def hibp_email(
    db: AsyncSession = Depends(get_db),
    user_id: str = Depends(get_current_user)
):
    result = await db.execute(select(User).where(User.id == user_id))
    user =  result.scalar_one_or_none()

    return await check_email_breach(user.email)