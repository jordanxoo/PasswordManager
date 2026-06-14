from sqlalchemy import select, delete
from fastapi import HTTPException
import logging
import secrets
import hashlib
from datetime import datetime, timedelta
from app.models.models import (
    Organization, OrganizationMembership, OrganizationInvitation, User,
    Vault, VaultHistory,
)
from app.models.enums import OrgRole

logger = logging.getLogger(__name__)

INVITE_TTL = timedelta(days=7)


def _hash_token(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()

# Role hierarchy for permission checks: higher number => more privilege.
ROLE_RANK = {OrgRole.MEMBER: 1, OrgRole.ADMIN: 2, OrgRole.OWNER: 3}


async def get_membership(db, org_id, user_id):
    """Return the membership row for (org, user) or None."""
    result = await db.execute(
        select(OrganizationMembership).where(
            OrganizationMembership.org_id == org_id,
            OrganizationMembership.user_id == user_id,
        )
    )
    return result.scalar_one_or_none()


async def create_organization(db, user_id, name, wrapped_org_key):
    org = Organization(name=name, owner_id=user_id)
    db.add(org)
    await db.flush()  # assign org.id before creating the membership

    membership = OrganizationMembership(
        org_id=org.id,
        user_id=user_id,
        role=OrgRole.OWNER,
        wrapped_org_key=wrapped_org_key,
    )
    db.add(membership)
    await db.commit()
    await db.refresh(org)
    return org, membership


async def list_user_organizations(db, user_id):
    """Orgs the user belongs to, each paired with their role + wrapped key."""
    result = await db.execute(
        select(Organization, OrganizationMembership)
        .join(OrganizationMembership, OrganizationMembership.org_id == Organization.id)
        .where(OrganizationMembership.user_id == user_id)
        .order_by(Organization.created_at.asc())
    )
    return result.all()


async def list_members(db, org_id):
    result = await db.execute(
        select(OrganizationMembership, User)
        .join(User, User.id == OrganizationMembership.user_id)
        .where(OrganizationMembership.org_id == org_id)
        .order_by(OrganizationMembership.created_at.asc())
    )
    return result.all()


async def add_member(db, org_id, email, role, wrapped_org_key):
    result = await db.execute(select(User).where(User.email == email))
    user = result.scalar_one_or_none()

    if user is None:
        raise HTTPException(status_code=404, detail="User not found")
    if user.public_key is None:
        # Cannot wrap the org key for a user who has no keypair yet.
        raise HTTPException(
            status_code=400,
            detail="User has not set up encryption keys yet",
        )

    existing = await get_membership(db, org_id, user.id)
    if existing is not None:
        raise HTTPException(status_code=400, detail="User is already a member")

    membership = OrganizationMembership(
        org_id=org_id,
        user_id=user.id,
        role=role,
        wrapped_org_key=wrapped_org_key,
    )
    db.add(membership)
    await db.commit()
    await db.refresh(membership)
    return membership, user


async def remove_member(db, org_id, target_user_id, acting_membership):
    """Remove a member. Self-removal is allowed; otherwise requires ADMIN+.

    The organization owner cannot be removed (would orphan the org)."""
    is_self = str(acting_membership.user_id) == str(target_user_id)
    if not is_self and ROLE_RANK[acting_membership.role] < ROLE_RANK[OrgRole.ADMIN]:
        raise HTTPException(status_code=403, detail="Insufficient permissions")

    target = await get_membership(db, org_id, target_user_id)
    if target is None:
        raise HTTPException(status_code=404, detail="Member not found")
    _check_removable(target, acting_membership, is_self)

    await db.delete(target)
    await db.commit()
    return {"message": "removed"}


def _check_removable(target, acting_membership, is_self):
    """Shared removal guards: the owner is never removable, and only the owner
    may remove an admin (admins manage members, not each other)."""
    if target.role == OrgRole.OWNER:
        raise HTTPException(status_code=400, detail="Cannot remove the organization owner")
    if not is_self and target.role == OrgRole.ADMIN \
            and acting_membership.role != OrgRole.OWNER:
        raise HTTPException(status_code=403, detail="Only the owner can remove an admin")


async def update_settings(db, org_id, member_write):
    """Update org-level settings. Caller must be OWNER (enforced at the router)."""
    org = (await db.execute(
        select(Organization).where(Organization.id == org_id))).scalar_one_or_none()
    if org is None:
        raise HTTPException(status_code=404, detail="Organization not found")
    org.member_write = member_write
    await db.commit()
    await db.refresh(org)
    return org


async def create_invitation(db, org_id, email, role, invited_by):
    """Create a pending invitation and return (invitation, raw_token).

    The raw token is only ever delivered in the emailed link; we store its hash."""
    email = email.lower()
    user = (await db.execute(select(User).where(User.email == email))).scalar_one_or_none()
    if user is not None and await get_membership(db, org_id, user.id) is not None:
        raise HTTPException(status_code=400, detail="User is already a member")

    token = secrets.token_urlsafe(32)
    invitation = OrganizationInvitation(
        org_id=org_id,
        email=email,
        role=role,
        token_hash=_hash_token(token),
        status="pending",
        invited_by=invited_by,
        expires_at=datetime.now() + INVITE_TTL,
    )
    db.add(invitation)
    await db.commit()
    await db.refresh(invitation)
    return invitation, token


async def list_invitations(db, org_id):
    result = await db.execute(
        select(OrganizationInvitation)
        .where(OrganizationInvitation.org_id == org_id,
               OrganizationInvitation.status == "pending")
        .order_by(OrganizationInvitation.created_at.desc())
    )
    return result.scalars().all()


async def revoke_invitation(db, org_id, invite_id):
    invite = (await db.execute(
        select(OrganizationInvitation).where(
            OrganizationInvitation.id == invite_id,
            OrganizationInvitation.org_id == org_id))).scalar_one_or_none()
    if invite is None:
        raise HTTPException(status_code=404, detail="Invitation not found")
    invite.status = "revoked"
    await db.commit()
    return {"message": "revoked"}


async def lookup_invitation(db, token):
    invite = (await db.execute(
        select(OrganizationInvitation).where(
            OrganizationInvitation.token_hash == _hash_token(token)))).scalar_one_or_none()
    if invite is None:
        raise HTTPException(status_code=404, detail="Invitation not found")
    org = (await db.execute(
        select(Organization).where(Organization.id == invite.org_id))).scalar_one()
    return {
        "org_id": org.id,
        "org_name": org.name,
        "role": invite.role,
        "email": invite.email,
        "status": invite.status,
        "expired": invite.expires_at < datetime.now(),
    }


async def accept_invitation(db, token, user_id, user_email):
    invite = (await db.execute(
        select(OrganizationInvitation).where(
            OrganizationInvitation.token_hash == _hash_token(token)))).scalar_one_or_none()
    if invite is None:
        raise HTTPException(status_code=404, detail="Invitation not found")
    if invite.status != "pending":
        raise HTTPException(status_code=400, detail="Invitation is no longer valid")
    if invite.expires_at < datetime.now():
        raise HTTPException(status_code=400, detail="Invitation has expired")
    if invite.email.lower() != user_email.lower():
        raise HTTPException(status_code=403, detail="This invitation is for a different email")

    if await get_membership(db, invite.org_id, user_id) is not None:
        invite.status = "accepted"
        await db.commit()
        raise HTTPException(status_code=400, detail="You are already a member")

    # Join as pending confirmation — no org key until an admin confirms.
    membership = OrganizationMembership(
        org_id=invite.org_id,
        user_id=user_id,
        role=invite.role,
        wrapped_org_key=None,
    )
    db.add(membership)
    invite.status = "accepted"
    await db.commit()
    return invite.org_id


async def confirm_member(db, org_id, target_user_id, wrapped_org_key):
    """Grant a pending member access by storing their wrapped org key."""
    target = await get_membership(db, org_id, target_user_id)
    if target is None:
        raise HTTPException(status_code=404, detail="Member not found")
    target.wrapped_org_key = wrapped_org_key
    await db.commit()
    await db.refresh(target)
    return target


async def rotate_org_key(db, org_id, remove_user_id, member_keys, vault_items, acting_membership):
    """Re-key an organization: store the new wrapped org key for every remaining
    confirmed member and replace every shared entry's ciphertext — atomically.

    Old ciphertext is purged so a removed member's cached key becomes useless.
    All crypto happens client-side; the server only persists the new blobs."""
    # 1. Optionally remove a member as part of the same atomic operation.
    if remove_user_id is not None:
        target = await get_membership(db, org_id, remove_user_id)
        if target is None:
            raise HTTPException(status_code=404, detail="Member not found")
        is_self = str(acting_membership.user_id) == str(remove_user_id)
        _check_removable(target, acting_membership, is_self)
        await db.delete(target)
        await db.flush()

    # 2. The new wrapped keys must cover exactly the remaining confirmed members.
    confirmed = (await db.execute(
        select(OrganizationMembership).where(
            OrganizationMembership.org_id == org_id,
            OrganizationMembership.wrapped_org_key.isnot(None)))).scalars().all()
    by_user = {str(m.user_id): m for m in confirmed}
    provided = {str(mk.user_id): mk.wrapped_org_key for mk in member_keys}
    if set(provided) != set(by_user):
        raise HTTPException(
            status_code=400,
            detail="member_keys must cover exactly the remaining confirmed members")

    # 3. The re-encrypted items must cover exactly the active shared entries.
    rows = (await db.execute(
        select(Vault).where(Vault.org_id == org_id))).scalars().all()
    active = {str(v.id): v for v in rows if not v.is_deleted}
    provided_items = {str(i.id): i for i in vault_items}
    if set(provided_items) != set(active):
        raise HTTPException(
            status_code=400,
            detail="vault_items must cover exactly the active shared entries")

    # 4. Apply: new wrapped keys + new ciphertext.
    for uid, wrapped in provided.items():
        by_user[uid].wrapped_org_key = wrapped
    for vid, item in provided_items.items():
        active[vid].encrypted = item.encrypted
        active[vid].iv = item.iv

    # 5. Purge any remaining old-key ciphertext: shared-entry history + org trash.
    org_vault_ids = select(Vault.id).where(Vault.org_id == org_id)
    await db.execute(delete(VaultHistory).where(VaultHistory.vault_id.in_(org_vault_ids)))
    await db.execute(delete(Vault).where(Vault.org_id == org_id, Vault.is_deleted == True))

    await db.commit()
    return {"message": "rotated"}


async def change_member_role(db, org_id, target_user_id, new_role):
    """Change a member's role. Caller must be OWNER (enforced at the router).

    The owner's own role is immutable here."""
    target = await get_membership(db, org_id, target_user_id)
    if target is None:
        raise HTTPException(status_code=404, detail="Member not found")
    if target.role == OrgRole.OWNER:
        raise HTTPException(status_code=400, detail="Cannot change the owner's role")
    if new_role == OrgRole.OWNER:
        raise HTTPException(status_code=400, detail="Cannot assign owner role")

    target.role = new_role
    await db.commit()
    await db.refresh(target)
    return target
