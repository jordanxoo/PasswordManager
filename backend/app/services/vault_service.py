from sqlalchemy import select
from fastapi import HTTPException
from app.models.models import Vault
import logging
from datetime import datetime
from app.models.enums import Category
from app.metrics import vault_operations_total
logger = logging.getLogger(__name__)
from sqlalchemy import select,or_,and_
import base64
import json
from uuid import UUID

async def get_vaults(db, user_id, category=None, cursor=None, limit=20):
    query = select(Vault).where(Vault.user_id == user_id)
    
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

    db.add(vault)
    await db.commit()
    await db.refresh(vault)
    vault_operations_total.labels("create").inc()
    return vault

async def update_vault(db,user_id,vault_id,data):

    result = await db.execute(select(Vault).where(Vault.id == vault_id))
    vault  = result.scalar_one_or_none()

    if vault is None:
        logger.error("Vault not found with provided ID")
        raise HTTPException(status_code=404,detail="Not Found")
    
    elif str(vault.user_id) != user_id:
        logger.error("Vault user id doesnt match provided user_id")
        raise HTTPException(status_code=403,detail="Forbidden")
    
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
    
    await db.delete(vault)
    await db.commit()
    vault_operations_total.labels("delete").inc()
    return {
        "message":"deleted"
    }


async def export_vaults(db,user_id):
    result = await db.execute(
        select(Vault).where(Vault.user_id == user_id)
    )
    vaults = result.scalars().all()

    vault_operations_total.labels("read").inc()

    return vaults

async def import_vaults(db,user_id,entries):
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