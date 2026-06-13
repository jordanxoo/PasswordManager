from fastapi import APIRouter, Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession
from uuid import UUID

from app.database import get_db
from app.dependencies import get_current_user, require_org_role
from app.models.enums import OrgRole, EventType
from app.schemas.organization import (
    OrganizationCreate, OrganizationResponse,
    MemberAddRequest, MemberResponse, RoleUpdateRequest, OrgSettingsRequest,
)
from app.services.organization_service import (
    create_organization, list_user_organizations, list_members,
    add_member, remove_member, change_member_role, update_settings,
)
from app.services.audit_service import log_event

router = APIRouter()


@router.post("/", response_model=OrganizationResponse)
async def create_organization_endpoint(
    request: Request,
    data: OrganizationCreate,
    db: AsyncSession = Depends(get_db),
    user_id: str = Depends(get_current_user)):

    org, membership = await create_organization(db, user_id, data.name, data.wrapped_org_key)
    await log_event(db, EventType.ORG_CREATED, request.client.host,
                    request.headers.get("user-agent"), user_id,
                    metadata={"org_id": str(org.id)})
    return OrganizationResponse(
        id=org.id, name=org.name, created_at=org.created_at,
        role=membership.role, wrapped_org_key=membership.wrapped_org_key,
        member_write=org.member_write,
    )


@router.get("/", response_model=list[OrganizationResponse])
async def list_organizations_endpoint(
    db: AsyncSession = Depends(get_db),
    user_id: str = Depends(get_current_user)):

    rows = await list_user_organizations(db, user_id)
    return [
        OrganizationResponse(
            id=org.id, name=org.name, created_at=org.created_at,
            role=membership.role, wrapped_org_key=membership.wrapped_org_key,
            member_write=org.member_write,
        )
        for org, membership in rows
    ]


@router.patch("/{org_id}/settings", response_model=OrganizationResponse)
async def update_settings_endpoint(
    org_id: UUID,
    data: OrgSettingsRequest,
    db: AsyncSession = Depends(get_db),
    membership = Depends(require_org_role(OrgRole.OWNER))):

    org = await update_settings(db, org_id, data.member_write)
    return OrganizationResponse(
        id=org.id, name=org.name, created_at=org.created_at,
        role=membership.role, wrapped_org_key=membership.wrapped_org_key,
        member_write=org.member_write,
    )


@router.get("/{org_id}/members", response_model=list[MemberResponse])
async def list_members_endpoint(
    org_id: UUID,
    db: AsyncSession = Depends(get_db),
    _membership = Depends(require_org_role(OrgRole.MEMBER))):

    rows = await list_members(db, org_id)
    return [
        MemberResponse(
            user_id=user.id, email=user.email,
            role=membership.role, created_at=membership.created_at,
        )
        for membership, user in rows
    ]


@router.post("/{org_id}/members", response_model=MemberResponse)
async def add_member_endpoint(
    request: Request,
    org_id: UUID,
    data: MemberAddRequest,
    db: AsyncSession = Depends(get_db),
    membership = Depends(require_org_role(OrgRole.ADMIN))):

    new_membership, user = await add_member(db, org_id, data.email, data.role, data.wrapped_org_key)
    await log_event(db, EventType.ORG_MEMBER_ADDED, request.client.host,
                    request.headers.get("user-agent"), str(membership.user_id),
                    metadata={"org_id": str(org_id), "member_id": str(user.id)})
    return MemberResponse(
        user_id=user.id, email=user.email,
        role=new_membership.role, created_at=new_membership.created_at,
    )


@router.patch("/{org_id}/members/{target_user_id}", response_model=MemberResponse)
async def change_role_endpoint(
    request: Request,
    org_id: UUID,
    target_user_id: UUID,
    data: RoleUpdateRequest,
    db: AsyncSession = Depends(get_db),
    membership = Depends(require_org_role(OrgRole.OWNER))):

    updated = await change_member_role(db, org_id, target_user_id, data.role)
    await log_event(db, EventType.ORG_ROLE_CHANGED, request.client.host,
                    request.headers.get("user-agent"), str(membership.user_id),
                    metadata={"org_id": str(org_id), "member_id": str(target_user_id),
                              "role": data.role.value})
    # Re-fetch the email for the response.
    from app.models.models import User
    from sqlalchemy import select
    user = (await db.execute(select(User).where(User.id == target_user_id))).scalar_one()
    return MemberResponse(
        user_id=user.id, email=user.email,
        role=updated.role, created_at=updated.created_at,
    )


@router.delete("/{org_id}/members/{target_user_id}")
async def remove_member_endpoint(
    request: Request,
    org_id: UUID,
    target_user_id: UUID,
    db: AsyncSession = Depends(get_db),
    membership = Depends(require_org_role(OrgRole.MEMBER))):

    result = await remove_member(db, org_id, target_user_id, membership)
    await log_event(db, EventType.ORG_MEMBER_REMOVED, request.client.host,
                    request.headers.get("user-agent"), str(membership.user_id),
                    metadata={"org_id": str(org_id), "member_id": str(target_user_id)})
    return result
