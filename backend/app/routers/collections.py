from fastapi import APIRouter, Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession
from uuid import UUID

from app.database import get_db
from app.dependencies import require_org_role
from app.models.enums import OrgRole
from app.schemas.organization import (
    CollectionCreate, CollectionResponse, CollectionAccessGrant, CollectionMemberResponse,
)
from app.services.collection_service import (
    create_collection, list_collections, list_collection_members,
    grant_access, revoke_access, delete_collection,
)

# Mounted at /organizations/{org_id}/collections
router = APIRouter()


@router.post("/", response_model=CollectionResponse)
async def create_collection_endpoint(
    org_id: UUID,
    data: CollectionCreate,
    db: AsyncSession = Depends(get_db),
    membership = Depends(require_org_role(OrgRole.ADMIN))):

    coll, access = await create_collection(db, org_id, data.name,
                                           membership.user_id, data.wrapped_collection_key)
    return CollectionResponse(id=coll.id, name=coll.name, created_at=coll.created_at,
                              wrapped_collection_key=access.wrapped_collection_key)


@router.get("/", response_model=list[CollectionResponse])
async def list_collections_endpoint(
    org_id: UUID,
    db: AsyncSession = Depends(get_db),
    membership = Depends(require_org_role(OrgRole.MEMBER))):

    rows = await list_collections(db, org_id, membership.user_id)
    return [
        CollectionResponse(id=coll.id, name=coll.name, created_at=coll.created_at,
                           wrapped_collection_key=access.wrapped_collection_key)
        for coll, access in rows
    ]


@router.get("/{collection_id}/members", response_model=list[CollectionMemberResponse])
async def list_collection_members_endpoint(
    org_id: UUID,
    collection_id: UUID,
    db: AsyncSession = Depends(get_db),
    membership = Depends(require_org_role(OrgRole.ADMIN))):

    rows = await list_collection_members(db, org_id, collection_id)
    return [
        CollectionMemberResponse(user_id=user.id, email=user.email, created_at=access.created_at)
        for access, user in rows
    ]


@router.post("/{collection_id}/access", response_model=CollectionMemberResponse)
async def grant_access_endpoint(
    org_id: UUID,
    collection_id: UUID,
    data: CollectionAccessGrant,
    db: AsyncSession = Depends(get_db),
    membership = Depends(require_org_role(OrgRole.ADMIN))):

    access, user = await grant_access(db, org_id, collection_id, data.email,
                                      data.wrapped_collection_key)
    return CollectionMemberResponse(user_id=user.id, email=user.email,
                                    created_at=access.created_at)


@router.delete("/{collection_id}/access/{user_id}")
async def revoke_access_endpoint(
    org_id: UUID,
    collection_id: UUID,
    user_id: UUID,
    db: AsyncSession = Depends(get_db),
    membership = Depends(require_org_role(OrgRole.ADMIN))):

    return await revoke_access(db, org_id, collection_id, user_id)


@router.delete("/{collection_id}")
async def delete_collection_endpoint(
    org_id: UUID,
    collection_id: UUID,
    db: AsyncSession = Depends(get_db),
    membership = Depends(require_org_role(OrgRole.ADMIN))):

    return await delete_collection(db, org_id, collection_id)
