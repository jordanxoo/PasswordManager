from sqlalchemy import select
from fastapi import HTTPException
from app.models.models import Vault
import logging
from datetime import datetime

logger = logging.getLogger(__name__)

async def get_vaults(db,user_id):
    
    result = await db.execute(select(Vault).where(Vault.user_id == user_id))
    vaults = result.scalars().all()
    return vaults


async def create_vault(db,user_id,data):

    vault = Vault(
        user_id = user_id,
        name = data.name,
        url = data.url,
        encrypted = data.encrypted,
        iv = data.iv,
    )

    db.add(vault)
    await db.commit()
    await db.refresh(vault)
    return vault

async def update_vault(db,user_id,vault_id,data):

    result = await db.execute(select(Vault).where(Vault.id == vault_id))
    vault  = result.scalar_one_or_none()

    if vault is None:
        logger.error("Vault not found with provided ID")
        raise HTTPException(status_code=404,detail="Not Found")
    
    elif vault.user_id != user_id:
        logger.error("Vault user id doesnt match provided user_id")
        raise HTTPException(status_code=403,detail="Forbidden")
    
    vault.name = data.name
    vault.url = data.url
    vault.encrypted = data.encrypted
    vault.iv = data.iv
    vault.updated_at = datetime.now()

    await db.commit()
    await db.refresh(vault)
    return vault
    

async def delete_vault(db,user_id,vault_id):

    result = await db.execute(select(Vault).where(Vault.id == vault_id))
    vault = result.scalar_one_or_none()

    if vault is None:
        logger.error("Vault not found")
        raise HTTPException(status_code=404,detail="Not Found")
    
    if vault.user_id != user_id:
        logger.error("Vault user id doesnt match provided user id")
        raise HTTPException(status_code=403,detail="Forbidden")
    
    await db.delete(vault)
    await db.commit()

    return {
        "message":"deleted"
    }