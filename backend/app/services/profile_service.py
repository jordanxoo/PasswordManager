from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select,delete
from fastapi import HTTPException
from app.models.models import User,RefreshToken,Vault,AuditLog
from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError


ph = PasswordHasher()

def _verify_password(stored_hash: str, password: str):
    try:
        ph.verify(stored_hash,password)
    except VerifyMismatchError:
        raise HTTPException(status_code=401,detail="Invalid password")
    

async def _get_user(db:AsyncSession, user_id: str) -> User:
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()

    if user is None:
        raise HTTPException(status_code=404, detail="User not found")
    
    return user

async def get_profile(db: AsyncSession,user_id: str):
    return await _get_user(db,user_id)

async def change_email(db:AsyncSession,user_id:str,new_email:str, current_password:str):
    user = await _get_user(db,user_id)
    _verify_password(user.password,current_password)

    existing = await db.execute(select(User).where(User.email == new_email))
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=409, detail="Email already in use")
    
    user.email = new_email
    await db.commit()


async def change_password(db:AsyncSession,user_id: str, new_password:str,current_password: str, salt: str):

    user = await _get_user(db,user_id)
    _verify_password(user.password,current_password)

    user.password = ph.hash(new_password)
    user.salt = salt
    await db.commit()

    await db.execute(delete(RefreshToken).where(RefreshToken.user_id == user_id))
    await db.commit()

async def delete_account(db: AsyncSession,user_id: str,current_password: str):
    user = await _get_user(db,user_id)
    _verify_password(user.password,current_password)

    await db.execute(delete(RefreshToken).where(user_id == RefreshToken.user_id))
    await db.execute(delete(Vault).where(Vault.user_id == user_id))
    await db.execute(delete(AuditLog).where(AuditLog.user_id == user_id))
    await db.delete(user)
    await db.commit()

async def get_sessions(db: AsyncSession, user_id: str):
    result = await db.execute(select(RefreshToken).where(RefreshToken.user_id == user_id))
    return result.scalars().all()

async def revoke_session(db:AsyncSession,user_id:str,session_id:str):
    result = await db.execute(
          select(RefreshToken).where(RefreshToken.id == session_id, RefreshToken.user_id == user_id)
      )
    session = result.scalar_one_or_none()
    if session is None:
        raise HTTPException(status_code=404, detail="Session not found")
    await db.delete(session)
    await db.commit()

async def revoke_all_sessions(db: AsyncSession, user_id: str, current_token: str):
    result = await db.execute(
        select(RefreshToken).where(RefreshToken.user_id == user_id)
    )
    sessions = result.scalars().all()
    for session in sessions:
        if session.token != current_token:
            await db.delete(session)
    await db.commit()

async def get_audit_log(db: AsyncSession, user_id: str):
    result = await db.execute(
        select(AuditLog)
        .where(AuditLog.user_id == user_id)
        .order_by(AuditLog.created_at.desc())
        .limit(50)
    )
    return result.scalars().all()
