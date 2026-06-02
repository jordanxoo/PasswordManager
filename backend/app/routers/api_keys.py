from fastapi import APIRouter,Depends
from app.database import get_db
from app.dependencies import get_current_user
from app.services.api_key_service import create_api_key,get_user_api_keys,revoke_api_key
from app.schemas.api_keys import ApiKeyCreateRequest,ApiKeyCreateResponse,ApiKeyListItem
from sqlalchemy.ext.asyncio import AsyncSession
from uuid import UUID


router = APIRouter()

@router.post("/",response_model=ApiKeyCreateResponse)
async def create_key_endpoint(
    data: ApiKeyCreateRequest,
    db: AsyncSession = Depends(get_db),
    user_id: str = Depends(get_current_user)
):
    record, raw = await create_api_key(db,user_id,data.name,data.scope,data.expires_at)

    return ApiKeyCreateResponse(
        id = record.id,
        name = record.name,
        scope = record.scope,
        key = raw,
        expires_at = record.expires_at,
        created_at = record.created_at
    )


@router.get("/",response_model=list[ApiKeyListItem])
async def list_keys_endpoint(
    db: AsyncSession = Depends(get_db),
    user_id: str = Depends(get_current_user)
):
    
    return await get_user_api_keys(db,user_id)

@router.delete("/{key_id}")
async def revoke_key_endpoint(
    key_id: UUID,
    db: AsyncSession = Depends(get_db),
    user_id: str = Depends(get_current_user)
):
    await revoke_api_key(db,user_id,key_id)
    return {"message": "API key revoked"}