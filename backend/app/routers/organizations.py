from fastapi import APIRouter, Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession
from uuid import UUID

from app.database import get_db
from app.dependencies import get_current_user, require_org_role
from app.models.enums import OrgRole, EventType
from app.models.models import User, Organization
from sqlalchemy import select
from app.schemas.organization import (
    OrganizationCreate, OrganizationResponse,
    MemberAddRequest, MemberResponse, RoleUpdateRequest, OrgSettingsRequest,
    InvitationCreate, InvitationResponse, InvitationLookupResponse,
    AcceptInviteRequest, ConfirmMemberRequest, RotateKeyRequest,
)
from app.services.organization_service import (
    create_organization, list_user_organizations, list_members,
    add_member, remove_member, change_member_role, update_settings,
    create_invitation, list_invitations, revoke_invitation,
    lookup_invitation, accept_invitation, confirm_member, rotate_org_key,
)
from app.services.audit_service import log_event
from app.publishers.notification_publisher import publish_email
from app.config import settings

router = APIRouter()


async def _current_user(db, user_id) -> User:
    return (await db.execute(select(User).where(User.id == user_id))).scalar_one()


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


# --- invitations (static paths declared before parametric /{org_id}/... routes) ---

@router.get("/invitations/lookup", response_model=InvitationLookupResponse)
async def lookup_invitation_endpoint(
    token: str,
    db: AsyncSession = Depends(get_db),
    user_id: str = Depends(get_current_user)):

    return await lookup_invitation(db, token)


@router.post("/invitations/accept")
async def accept_invitation_endpoint(
    data: AcceptInviteRequest,
    db: AsyncSession = Depends(get_db),
    user_id: str = Depends(get_current_user)):

    user = await _current_user(db, user_id)
    org_id = await accept_invitation(db, data.token, user_id, user.email)
    return {"org_id": str(org_id)}


@router.post("/{org_id}/invitations", response_model=InvitationResponse)
async def create_invitation_endpoint(
    request: Request,
    org_id: UUID,
    data: InvitationCreate,
    db: AsyncSession = Depends(get_db),
    membership = Depends(require_org_role(OrgRole.ADMIN))):

    invitation, token = await create_invitation(db, org_id, data.email, data.role,
                                                membership.user_id)
    org = (await db.execute(select(Organization).where(Organization.id == org_id))).scalar_one()
    link = f"{settings.FRONTEND_URL}/invite?token={token}"
    await publish_email(
        to=invitation.email,
        subject=f"Zaproszenie do organizacji {org.name}",
        body=(f"Zostales zaproszony do organizacji {org.name} w Password Manager.\n\n"
              f"Aby dolaczyc, otworz link (zaloguj sie lub zaloz konto na ten adres e-mail):\n"
              f"{link}\n\nLink wygasa za 7 dni."),
    )
    await log_event(db, EventType.ORG_MEMBER_ADDED, request.client.host,
                    request.headers.get("user-agent"), str(membership.user_id),
                    metadata={"org_id": str(org_id), "invited": invitation.email})
    return invitation


@router.get("/{org_id}/invitations", response_model=list[InvitationResponse])
async def list_invitations_endpoint(
    org_id: UUID,
    db: AsyncSession = Depends(get_db),
    membership = Depends(require_org_role(OrgRole.ADMIN))):

    return await list_invitations(db, org_id)


@router.delete("/{org_id}/invitations/{invite_id}")
async def revoke_invitation_endpoint(
    org_id: UUID,
    invite_id: UUID,
    db: AsyncSession = Depends(get_db),
    membership = Depends(require_org_role(OrgRole.ADMIN))):

    return await revoke_invitation(db, org_id, invite_id)


@router.post("/{org_id}/members/{target_user_id}/confirm", response_model=MemberResponse)
async def confirm_member_endpoint(
    request: Request,
    org_id: UUID,
    target_user_id: UUID,
    data: ConfirmMemberRequest,
    db: AsyncSession = Depends(get_db),
    membership = Depends(require_org_role(OrgRole.ADMIN))):

    updated = await confirm_member(db, org_id, target_user_id, data.wrapped_org_key)
    user = await _current_user(db, target_user_id)
    await log_event(db, EventType.ORG_MEMBER_ADDED, request.client.host,
                    request.headers.get("user-agent"), str(membership.user_id),
                    metadata={"org_id": str(org_id), "confirmed_member": str(target_user_id)})
    return MemberResponse(
        user_id=user.id, email=user.email, role=updated.role,
        created_at=updated.created_at, confirmed=True,
    )


@router.post("/{org_id}/rotate-key")
async def rotate_key_endpoint(
    request: Request,
    org_id: UUID,
    data: RotateKeyRequest,
    db: AsyncSession = Depends(get_db),
    membership = Depends(require_org_role(OrgRole.ADMIN))):

    result = await rotate_org_key(db, org_id, data.remove_user_id,
                                  data.member_keys, data.vault_items)
    meta = {"org_id": str(org_id)}
    if data.remove_user_id is not None:
        meta["removed_member"] = str(data.remove_user_id)
    await log_event(db, EventType.ORG_MEMBER_REMOVED, request.client.host,
                    request.headers.get("user-agent"), str(membership.user_id), metadata=meta)
    return result


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
            confirmed=membership.wrapped_org_key is not None,
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
