from sqlalchemy import select
from fastapi import HTTPException
from app.models.models import Vault
import logging
from datetime import datetime
from app.models.enums import Category
logger = logging.getLogger(__name__)

async def get_vaults(db,user_id,category = None):
    
    query = select(Vault).where(Vault.user_id == user_id)
    
    if category:
        query = query.where(Vault.category == category)
    
    result = await db.execute(query)

    return result.scalars().all()
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
    vault.expires_at = data.expires_at
    vault.category = data.category
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