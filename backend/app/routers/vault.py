from fastapi import APIRouter,Depends,Request
from app.database import get_db
from app.dependencies import get_current_user
from app.services.vault_service import get_vaults,create_vault,delete_vault,update_vault,export_vaults,import_vaults,get_vault_history,restore_vault
from sqlalchemy.ext.asyncio import  AsyncSession
from uuid import UUID
from app.services.audit_service import log_event,EventType
from app.publishers.vault_publisher import publish_vault_event
from app.models.enums import Category
from typing import Optional
from app.schemas.vault import VaultCreate,VaultResponse,VaultPaginatedResponse,VaultExportResponse,VaultImportRequest,VaultUpdate,VaultHistoryResponse
from datetime import datetime
router = APIRouter()

@router.get("/", response_model=VaultPaginatedResponse)
async def get_vaults_endpoint(
    request: Request,
    db: AsyncSession = Depends(get_db),
    user_id: str = Depends(get_current_user),
    category: Optional[Category] = None,
    cursor: Optional[str] = None,
    limit: int = 20):

    items, next_cursor, has_next = await get_vaults(db, user_id, category, cursor, limit)
    await publish_vault_event("read", user_id)
    await log_event(db, EventType.VAULT_READ, request.client.host,
                    request.headers.get("user-agent"), user_id)
    return VaultPaginatedResponse(items=items, next_cursor=next_cursor, has_next=has_next)


@router.post("/",response_model=VaultResponse)
async def create_vault_endpoint(
    request: Request,
    data: VaultCreate,
    db:AsyncSession = Depends(get_db),
    user_id: str = Depends(get_current_user)):

    result = await create_vault(db,user_id,data)
    await publish_vault_event("create",user_id,str(result.id))
    await log_event(db,EventType.VAULT_CREATE,request.client.host,
                    request.headers.get("user-agent"),user_id)

    return result

@router.get("/export",response_model=VaultExportResponse)
async def export_vault_endpoint(
    request: Request,
    db: AsyncSession = Depends(get_db),
    user_id: str = Depends(get_current_user)):
    
    items = await export_vaults(db,user_id)
    await log_event(db,EventType.VAULT_READ,request.client.host,
                    request.headers.get("user-agent"),user_id)
    

    return VaultExportResponse(exported_at=datetime.now(),items=items)
 



@router.post("/import")
async def import_vault_endpoint(
    request: Request,
    data: VaultImportRequest,
    db: AsyncSession = Depends(get_db),
    user_id: str = Depends(get_current_user)):

    count = await import_vaults(db,user_id,data.items)
    await log_event(db,EventType.VAULT_CREATE,request.client.host,
                    request.headers.get("user-agent"),user_id)
    

    return{"imported": count}

@router.get("/{vault_id}/history",response_model=list[VaultHistoryResponse])
async def get_vault_history_endpoint(
    vault_id:UUID,
    db:AsyncSession = Depends(get_db),
    user_id: str = Depends(get_current_user)):
    
    return await get_vault_history(db,user_id,vault_id)

@router.post("/{vault_id}/restore/{history_id}")
async def  restore_vault_endpoint(
    vault_id: UUID,
    history_id: UUID,
    db: AsyncSession = Depends(get_db),
    user_id: str = Depends(get_current_user)):

    return await restore_vault(db,user_id,vault_id,history_id)



@router.put("/{vault_id}",response_model=VaultResponse)
async def update_vault_endpoint(
    request: Request,
    vault_id:UUID,
    data:VaultUpdate,
    db: AsyncSession = Depends(get_db),
    user_id: str = Depends(get_current_user)):

    result =  await update_vault(db,user_id,vault_id,data)    
    await publish_vault_event("update",user_id,str(vault_id))
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
    await publish_vault_event("delete",user_id,str(vault_id))
    await log_event(db,EventType.VAULT_DELETE,request.client.host,
                    request.headers.get("user-agent"),user_id,metadata={"vault_id": str(vault_id)})
    
    return result



