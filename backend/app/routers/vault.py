from fastapi import APIRouter,Depends,Request
from app.database import get_db
from app.dependencies import get_current_user
from app.services.vault_service import get_vaults,create_vault,delete_vault,update_vault
from  app.schemas.vault import VaultCreate,VaultResponse,VaultUpdate
from sqlalchemy.ext.asyncio import  AsyncSession
from uuid import UUID
from app.services.audit_service import log_event,EventType
router = APIRouter()

@router.get("/",response_model=list[VaultResponse])
async def get_vaults_endpoint(request: Request,
    db: AsyncSession = Depends(get_db),
                     user_id: str = Depends(get_current_user)):    
    result =  await get_vaults(db,user_id)
    await log_event(db,EventType.VAULT_READ,request.client.host,
                    request.headers.get("user-agent"),user_id)
    return result

@router.post("/",response_model=VaultResponse)
async def create_vault_endpoint(
    request: Request,
    data: VaultCreate,
    db:AsyncSession = Depends(get_db),
    user_id: str = Depends(get_current_user)):

    result = await create_vault(db,user_id,data)

    await log_event(db,EventType.VAULT_CREATE,request.client.host,
                    request.headers.get("user-agent"),user_id)

    return result

@router.put("/{vault_id}",response_model=VaultResponse)
async def update_vault_endpoint(
    request: Request,
    vault_id:UUID,
    data:VaultUpdate,
    db: AsyncSession = Depends(get_db),
    user_id: str = Depends(get_current_user)):

    result =  await update_vault(db,user_id,vault_id,data)    
    
    await log_event(db,EventType.VAULT_UPDATE,request.client.host,
                    request.headers.get("user-agent"),user_id,metadata={"vault_id":str(vault_id)}
    )
    return result

@router.delete("/{vault_id}")
async def delete_vault_endpoint(
    request: Request,
    vault_id: UUID,
    db: AsyncSession = Depends(get_db),
    user_id: str = Depends(get_current_user)):

    result =  await delete_vault(db,user_id,vault_id)   

    await log_event(db,EventType.VAULT_DELETE,request.client.host,
                    request.headers.get("user-agent"),user_id,metadata={"vault_id": str(vault_id)})
    
    return result