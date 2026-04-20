from fastapi import APIRouter,Depends
from app.database import get_db
from app.dependencies import get_current_user
from app.services.vault_service import get_vaults,create_vault,delete_vault,update_vault
from  app.schemas.vault import VaultCreate,VaultResponse,VaultUpdate
from sqlalchemy.ext.asyncio import  AsyncSession
from uuid import UUID
router = APIRouter()

@router.get("/",response_model=list[VaultResponse])
async def get_vaults_endpoint(db: AsyncSession = Depends(get_db),
                     user_id: str = Depends(get_current_user)):    
    return await get_vaults(db,user_id)


@router.post("/",response_model=VaultResponse)
async def create_vault_endpoint(
    data: VaultCreate,
    db:AsyncSession = Depends(get_db),
    user_id: str = Depends(get_current_user)):

    return await create_vault(db,user_id,data)

@router.put("/{vault_id}",response_model=VaultResponse)
async def update_vault_endpoint(
    vault_id:UUID,
    data:VaultUpdate,
    db: AsyncSession = Depends(get_db),
    user_id: str = Depends(get_current_user)):

    return await update_vault(db,user_id,vault_id,data)    


@router.delete("/{vault_id}")
async def delete_vault_endpoint(
    vault_id: UUID,
    db: AsyncSession = Depends(get_db),
    user_id: str = Depends(get_current_user)):

    return await delete_vault(db,user_id,vault_id)