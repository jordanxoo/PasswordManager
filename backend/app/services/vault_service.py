from sqlalchemy import select
from fastapi import HTTPException
import logging
from datetime import datetime
from app.models.enums import Category
from app.metrics import vault_operations_total
logger = logging.getLogger(__name__)
from sqlalchemy import select,or_,and_,func
import base64
import json
from app.models.models import Vault,VaultHistory
from sqlalchemy import select,or_,and_,func,delete
from uuid import UUID

async def get_vaults(db, user_id, category=None, cursor=None, limit=20):
    query = select(Vault).where(Vault.user_id == user_id,Vault.is_deleted == False)
    
    if category:
        query = query.where(Vault.category == category)

    if cursor:
        data = json.loads(base64.b64decode(cursor))
        cursor_time = datetime.fromisoformat(data["created_at"])
        cursor_id = UUID(data["id"])
        query = query.where(
            or_(
                Vault.created_at > cursor_time,
                and_(Vault.created_at == cursor_time, Vault.id > cursor_id)
            )   
        )

    query = query.order_by(Vault.created_at.asc(), Vault.id.asc()).limit(limit + 1)
    
    result = await db.execute(query)
    vaults = result.scalars().all()
    
    has_next = len(vaults) > limit
    items = list(vaults[:limit])

    next_cursor = None
    if has_next:
        last = items[-1]
        next_cursor = base64.b64encode(json.dumps({
            "created_at": last.created_at.isoformat(),
            "id": str(last.id)
        }).encode()).decode()

    vault_operations_total.labels("read").inc()
    return items, next_cursor, has_next

async def create_vault(db,user_id,data):

    vault = Vault(
        user_id = user_id,
        name = data.name,
        url = data.url,
        encrypted = data.encrypted,
        iv = data.iv,
        expires_at = data.expires_at,
        category = data.category
    )
    count = await get_vault_count(db,user_id)
    if count >= 1000:
        raise HTTPException(status_code=400, detail="Vault limit reached (max 1000 entries)")

    db.add(vault)
    await db.commit()
    await db.refresh(vault)
    vault_operations_total.labels("create").inc()
    return vault

async def update_vault(db, user_id, vault_id, data):
    result = await db.execute(select(Vault).where(Vault.id == vault_id))
    vault = result.scalar_one_or_none()

    if vault is None:
        logger.error("Vault not found with provided ID")
        raise HTTPException(status_code=404, detail="Not Found")

    if str(vault.user_id) != user_id:
        logger.error("Vault user id doesnt match provided user_id")
        raise HTTPException(status_code=403, detail="Forbidden")

    history = VaultHistory(
        vault_id=vault.id,
        name=vault.name,
        url=vault.url,
        encrypted=vault.encrypted,
        iv=vault.iv
    )
    db.add(history)

    count_result = await db.execute(
        select(func.count()).select_from(VaultHistory).where(VaultHistory.vault_id == vault.id)
    )
    history_count = count_result.scalar()

    if history_count >= 3:
        oldest = await db.execute(
            select(VaultHistory)
            .where(VaultHistory.vault_id == vault.id)
            .order_by(VaultHistory.changed_at.asc())
            .limit(1)
        )
        oldest_record = oldest.scalar_one_or_none()
        if oldest_record:
            await db.delete(oldest_record)

    vault.name = data.name
    vault.url = data.url
    vault.encrypted = data.encrypted
    vault.iv = data.iv
    vault.updated_at = datetime.now()
    vault.expires_at = data.expires_at
    vault.category = data.category
    await db.commit()
    await db.refresh(vault)
    vault_operations_total.labels("update").inc()
    return vault



async def delete_vault(db,user_id,vault_id):

    result = await db.execute(select(Vault).where(Vault.id == vault_id))
    vault = result.scalar_one_or_none()

    if vault is None:
        logger.error("Vault not found")
        raise HTTPException(status_code=404,detail="Not Found")
    
    if str(vault.user_id) != user_id:
        logger.error("Vault user id doesnt match provided user id")
        raise HTTPException(status_code=403,detail="Forbidden")
    
    vault.is_deleted = True
    await db.commit()
    vault_operations_total.labels("delete").inc()
    return {"message":"deleted"}

async def export_vaults(db,user_id):
    result = await db.execute(
        select(Vault).where(Vault.user_id == user_id)
    )
    vaults = result.scalars().all()

    vault_operations_total.labels("read").inc()

    return vaults

async def import_vaults(db,user_id,entries):
    
    
    count = await get_vault_count(db,user_id)
    if count + len(entries) >= 1000:
        raise HTTPException(status_code=400,detail="Import would exceed vault limit")
    
    vaults = []
    for entry in entries:
        vault = Vault(
            user_id = user_id,
            name = entry.name,
            url = entry.url,
            encrypted = entry.encrypted,
            iv = entry.iv,
            expires_at = entry.expires_at,
            category = entry.category
        )
        db.add(vault)
        vaults.append(vault)

    await db.commit()
    vault_operations_total.labels("create").inc()
    return len(vaults)

async def get_vault_count(db, user_id):
    result = await db.execute(
        select(func.count()).select_from(Vault).where(Vault.user_id == user_id)
    )
    return result.scalar()



async def  get_vault_history(db,user_id,vault_id):
    result = await db.execute(select(Vault).where(Vault.id == vault_id))
    vault = result.scalar_one_or_none()

    if vault is None or str(vault.user_id) != user_id:
        raise HTTPException(status_code=404,detail="Not found")
    
    history = await db.execute(
        select(VaultHistory).where(VaultHistory.vault_id == vault_id)
        .order_by(VaultHistory.changed_at.desc())
    )

    return history.scalars().all()


async def restore_vault(db,user_id,vault_id,history_id):
    result = await db.execute(select(Vault).where(Vault.id == vault_id))
    vault = result.scalar_one_or_none()

    if vault is None or str(vault.user_id) != user_id:
        raise HTTPException(status_code=404,detail="not found")
    
    history_result = await db.execute(
        select(VaultHistory).where(VaultHistory.id == history_id,
                                   VaultHistory.vault_id == vault_id)
    )

    history = history_result.scalar_one_or_none()

    if history is None:
        raise HTTPException(status_code=404,detail="History record not found")
    
    vault.name = history.name
    vault.url = history.url
    vault.encrypted = history.encrypted
    vault.iv = history.iv
    vault.updated_at = datetime.now()
    vault.is_deleted = False
    await db.commit()
    await db.refresh(vault)
    return vault
