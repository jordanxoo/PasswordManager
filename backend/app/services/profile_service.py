from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select,delete
from fastapi import HTTPException
from app.models.models import User,RefreshToken,Vault,AuditLog,VaultHistory,RecoveryCode,ApiKey
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

    # vault_history -> vaults is an FK without ON DELETE CASCADE, so history rows
    # must go before their vaults or the vault delete raises a FK violation.
    user_vault_ids = select(Vault.id).where(Vault.user_id == user_id)
    await db.execute(delete(VaultHistory).where(VaultHistory.vault_id.in_(user_vault_ids)))
    await db.execute(delete(Vault).where(Vault.user_id == user_id))

    # recovery_codes / api_keys -> users are also FKs without CASCADE, so they
    # must be cleared before deleting the user.
    await db.execute(delete(RecoveryCode).where(RecoveryCode.user_id == user_id))
    await db.execute(delete(ApiKey).where(ApiKey.user_id == user_id))
    await db.execute(delete(RefreshToken).where(RefreshToken.user_id == user_id))
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


async def set_keys(db: AsyncSession, user_id: str, public_key: str,
                   encrypted_private_key: str, private_key_iv: str):
    """Backfill the asymmetric keypair (legacy account migration). Refuses to
    overwrite an existing keypair — that would orphan any org keys wrapped to it."""
    user = await _get_user(db, user_id)
    if user.public_key is not None:
        raise HTTPException(status_code=400, detail="Keys already set")
    user.public_key = public_key
    user.encrypted_private_key = encrypted_private_key
    user.private_key_iv = private_key_iv
    await db.commit()


async def get_public_key(db: AsyncSession, email: str):
    result = await db.execute(select(User).where(User.email == email))
    user = result.scalar_one_or_none()
    if user is None:
        raise HTTPException(status_code=404, detail="User not found")
    if user.public_key is None:
        raise HTTPException(status_code=400, detail="User has not set up encryption keys yet")
    return {"user_id": user.id, "email": user.email, "public_key": user.public_key}
