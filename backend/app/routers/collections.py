from fastapi import APIRouter, Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession
from uuid import UUID

from app.database import get_db
from app.dependencies import require_org_role
from app.models.enums import OrgRole, EventType
from app.schemas.organization import (
    CollectionCreate, CollectionResponse, CollectionAccessGrant, CollectionMemberResponse,
    CollectionRotateRequest,
)
from app.services.collection_service import (
    create_collection, list_collections, list_collection_members,
    grant_access, revoke_access, delete_collection, rotate_collection_key,
)
from app.services.audit_service import log_event


async def _audit(db, request, event, membership, org_id, meta):
    await log_event(db, event, request.client.host, request.headers.get("user-agent"),
                    str(membership.user_id), metadata=meta, org_id=org_id)

# Mounted at /organizations/{org_id}/collections
router = APIRouter()


@router.post("/", response_model=CollectionResponse)
async def create_collection_endpoint(
    request: Request,
    org_id: UUID,
    data: CollectionCreate,
    db: AsyncSession = Depends(get_db),
    membership = Depends(require_org_role(OrgRole.ADMIN))):

    coll, access = await create_collection(db, org_id, data.name,
                                           membership.user_id, data.wrapped_collection_key)
    await _audit(db, request, EventType.COLLECTION_CREATED, membership, org_id,
                 {"collection_id": str(coll.id), "collection_name": coll.name})
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
    request: Request,
    org_id: UUID,
    collection_id: UUID,
    data: CollectionAccessGrant,
    db: AsyncSession = Depends(get_db),
    membership = Depends(require_org_role(OrgRole.ADMIN))):

    access, user = await grant_access(db, org_id, collection_id, data.email,
                                      data.wrapped_collection_key)
    await _audit(db, request, EventType.COLLECTION_ACCESS_GRANTED, membership, org_id,
                 {"collection_id": str(collection_id), "member": user.email})
    return CollectionMemberResponse(user_id=user.id, email=user.email,
                                    created_at=access.created_at)


@router.delete("/{collection_id}/access/{user_id}")
async def revoke_access_endpoint(
    request: Request,
    org_id: UUID,
    collection_id: UUID,
    user_id: UUID,
    db: AsyncSession = Depends(get_db),
    membership = Depends(require_org_role(OrgRole.ADMIN))):

    result = await revoke_access(db, org_id, collection_id, user_id)
    await _audit(db, request, EventType.COLLECTION_ACCESS_REVOKED, membership, org_id,
                 {"collection_id": str(collection_id), "member_id": str(user_id)})
    return result


@router.post("/{collection_id}/rotate-key")
async def rotate_collection_key_endpoint(
    request: Request,
    org_id: UUID,
    collection_id: UUID,
    data: CollectionRotateRequest,
    db: AsyncSession = Depends(get_db),
    membership = Depends(require_org_role(OrgRole.ADMIN))):

    result = await rotate_collection_key(db, org_id, collection_id, data.remove_user_id,
                                         data.member_keys, data.vault_items)
    meta = {"collection_id": str(collection_id)}
    if data.remove_user_id is not None:
        meta["removed_member"] = str(data.remove_user_id)
    await _audit(db, request, EventType.ORG_KEY_ROTATED, membership, org_id, meta)
    return result


@router.delete("/{collection_id}")
async def delete_collection_endpoint(
    request: Request,
    org_id: UUID,
    collection_id: UUID,
    db: AsyncSession = Depends(get_db),
    membership = Depends(require_org_role(OrgRole.ADMIN))):

    result = await delete_collection(db, org_id, collection_id)
    await _audit(db, request, EventType.COLLECTION_DELETED, membership, org_id,
                 {"collection_id": str(collection_id)})
    return result
