from sqlalchemy import select
from fastapi import HTTPException
import logging
from app.models.models import Organization, OrganizationMembership, User
from app.models.enums import OrgRole

logger = logging.getLogger(__name__)

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
    if target.role == OrgRole.OWNER:
        raise HTTPException(status_code=400, detail="Cannot remove the organization owner")

    await db.delete(target)
    await db.commit()
    return {"message": "removed"}


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
