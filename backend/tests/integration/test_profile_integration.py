import pytest
from sqlalchemy import select, func
from argon2 import PasswordHasher

from app.models.models import (
    User, Vault, VaultHistory, RecoveryCode, ApiKey, RefreshToken, AuditLog,
)
from app.models.enums import EventType
from app.services import profile_service

ph = PasswordHasher()


async def _seed_full_account(db):
    """A user touching every table that delete_account must clean up."""
    user = User(
        email="deluser@test.com",
        password=ph.hash("DelPass123!"),
        salt="delsalt",
    )
    db.add(user)
    await db.flush()

    vault = Vault(user_id=user.id, encrypted="enc", iv="dGVzdF9pdl9kYXRh")
    db.add(vault)
    await db.flush()

    # vault_history -> vaults; recovery_codes / api_keys / refresh_tokens -> users.
    # None of these FKs have ON DELETE CASCADE, so delete_account must clear them
    # by hand or the deletes raise a FK violation.
    db.add(VaultHistory(vault_id=vault.id, encrypted="old", iv="dGVzdF9pdl9kYXRh"))
    db.add(RecoveryCode(user_id=user.id, code_hash="hash"))
    db.add(ApiKey(user_id=user.id, key_hash="keyhash", name="k", scope="read"))
    db.add(RefreshToken(user_id=user.id, token="tok", family_id="fam",
                        expires_at=func.now()))
    db.add(AuditLog(user_id=user.id, event_type=EventType.LOGIN_SUCCESS))
    await db.commit()
    return user, vault


async def test_delete_account_removes_all_related_rows(db):
    user, vault = await _seed_full_account(db)

    await profile_service.delete_account(db, str(user.id), "DelPass123!")

    async def count(model, col, value):
        res = await db.execute(select(func.count()).select_from(model).where(col == value))
        return res.scalar()

    assert await count(User, User.id, user.id) == 0
    assert await count(Vault, Vault.user_id, user.id) == 0
    assert await count(VaultHistory, VaultHistory.vault_id, vault.id) == 0
    assert await count(RecoveryCode, RecoveryCode.user_id, user.id) == 0
    assert await count(ApiKey, ApiKey.user_id, user.id) == 0
    assert await count(RefreshToken, RefreshToken.user_id, user.id) == 0
    assert await count(AuditLog, AuditLog.user_id, user.id) == 0


async def test_delete_account_wrong_password_keeps_data(db):
    user, _ = await _seed_full_account(db)

    with pytest.raises(Exception):
        await profile_service.delete_account(db, str(user.id), "WrongPass!")

    res = await db.execute(select(func.count()).select_from(User).where(User.id == user.id))
    assert res.scalar() == 1
