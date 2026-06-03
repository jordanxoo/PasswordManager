import secrets
import hashlib
from datetime import datetime
from sqlalchemy import select,delete,func
from app.models.models import RecoveryCode



def generate_code() -> str:
    # Must match RecoveryValidateRequest's pattern ^[a-z0-9]{4}-[a-z0-9]{4}$ —
    # lowercase hex, a single hyphen, no spaces — or validation always 422s and
    # the stored hash never matches what the user types.
    raw = secrets.token_hex(4)
    return f"{raw[:4]}-{raw[4:]}"



def hash_code(code: str) -> str:
    return hashlib.sha256(code.encode()).hexdigest()

async def generate_recovery_codes(db,user_id) -> list[str]:
    await db.execute(delete(RecoveryCode).where(RecoveryCode.user_id == user_id))

    codes = []
    for _ in range(10):
        code = generate_code()
        codes.append(code)
        record = RecoveryCode(
            user_id = user_id,
            code_hash = hash_code(code)
        )
        db.add(record)

    await db.commit()
    return codes



async def validate_recovery_code(db,user_id,code) -> bool:
    code_hash = hash_code(code)

    result = await db.execute(select(RecoveryCode).where(
        RecoveryCode.user_id == user_id,
        RecoveryCode.code_hash == code_hash,
        RecoveryCode.is_used == False
    ))

    record = result.scalar_one_or_none()

    if record is None:
        return False
    
    record.is_used = True
    record.used_at = datetime.now()
    await db.commit()
    return True



async def get_remaining_count(db,user_id) -> dict:

    total_result = await db.execute(select(
        func.count()).select_from(RecoveryCode).where(RecoveryCode.user_id == user_id))

    total = total_result.scalar()

    remaining_count = await db.execute(
        select(func.count()).select_from(RecoveryCode).where(
            RecoveryCode.user_id == user_id,
            RecoveryCode.is_used == False
        )
    )

    remaining = remaining_count.scalar()

    return {"total":total,"remaining":remaining}