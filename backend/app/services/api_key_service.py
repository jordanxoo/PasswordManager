import secrets
import hashlib
from datetime import datetime
from sqlalchemy import select,delete
from app.models.models import ApiKey
from fastapi import HTTPException


def _hash_key(raw: str) -> str:
    return hashlib.sha256(raw.encode()).hexdigest()


async def create_api_key(db,user_id:str,name:str,scope: str, expires_at=None):
    raw = "pm_" + secrets.token_hex(32)
    record = ApiKey(
        user_id = user_id,
        key_hash = _hash_key(raw),
        name = name,
        scope = scope,
        expires_at = expires_at
    )

    db.add(record)
    await db.commit()
    await db.refresh(record)
    return record,raw


async def get_user_api_keys(db,user_id: str):
    result = await db.execute(select(ApiKey).where(ApiKey.user_id == user_id))

    return result.scalars().all()


async def revoke_api_key(db, user_id: str, key_id):
    result = await db.execute(select(ApiKey).where(ApiKey.user_id == user_id,ApiKey.id == key_id))

    record = result.scalar_one_or_none()

    if record is None:
        raise HTTPException(status_code=404,detail="API key not found")
    
    await db.execute(delete(ApiKey).where(ApiKey.id == key_id))
    await db.commit()


async def verify_api_key(db,raw_key:str):
    key_hash = _hash_key(raw_key)

    result = await db.execute(select(ApiKey).where(ApiKey.key_hash == key_hash))

    record = result.scalar_one_or_none()
    if record is None:
        return None
    if record.expires_at and record.expires_at < datetime.now():
        return None
    
    record.last_used_at = datetime.now()
    await db.commit()
    return str(record.user_id),record.scope