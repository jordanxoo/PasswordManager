from sqlalchemy import select
from fastapi import HTTPException
import logging
from datetime import datetime
from app.models.enums import Category
from app.metrics import vault_operations_total
logger = logging.getLogger(__name__)
from sqlalchemy import select,or_,and_,func
import base64
import json
from app.models.models import Vault,VaultHistory,Organization,Collection
from app.models.enums import OrgRole
from app.services.organization_service import get_membership, ROLE_RANK
from app.services.collection_service import get_collection_access
from sqlalchemy import select,or_,and_,func,delete
from uuid import UUID


async def _require_member(db, org_id, user_id, *, write):
    """Ensure the user belongs to the org; for writes also enforce the org's
    member_write policy (members are read-only when it is off)."""
    membership = await get_membership(db, org_id, user_id)
    if membership is None:
        raise HTTPException(status_code=403, detail="Not a member of this organization")
    if write:
        org = (await db.execute(
            select(Organization).where(Organization.id == org_id))).scalar_one_or_none()
        if org is None:
            raise HTTPException(status_code=404, detail="Organization not found")
        if not (org.member_write or ROLE_RANK[membership.role] >= ROLE_RANK[OrgRole.ADMIN]):
            raise HTTPException(status_code=403,
                                detail="Read-only: members cannot edit shared entries")
    return membership


async def _require_collection_access(db, collection_id, user_id, *, write):
    """Require the user has access to the collection; for writes also enforce the
    owning org's member_write policy (same rule as org-wide shared entries)."""
    if await get_collection_access(db, collection_id, user_id) is None:
        raise HTTPException(status_code=403, detail="No access to this collection")
    if write:
        coll = (await db.execute(
            select(Collection).where(Collection.id == collection_id))).scalar_one_or_none()
        if coll is None:
            raise HTTPException(status_code=404, detail="Collection not found")
        await _require_member(db, coll.org_id, user_id, write=True)


async def _authorize_vault(db, vault, user_id, *, write):
    """Authorize a single vault row: personal by ownership, org-wide 'General' by
    membership, collection entries by collection access (all with write policy)."""
    if vault.org_id is None:
        if str(vault.user_id) != user_id:
            raise HTTPException(status_code=403, detail="Forbidden")
    elif vault.collection_id is None:
        await _require_member(db, vault.org_id, user_id, write=write)
    else:
        await _require_collection_access(db, vault.collection_id, user_id, write=write)


async def get_vaults(db, user_id, category=None, cursor=None, limit=20, org_id=None,
                     collection_id=None):
    if collection_id is not None:
        await _require_collection_access(db, collection_id, user_id, write=False)
        query = select(Vault).where(Vault.collection_id == collection_id,
                                    Vault.is_deleted == False)
    elif org_id is not None:
        # Org-wide "General" — org entries not in any collection.
        await _require_member(db, org_id, user_id, write=False)
        query = select(Vault).where(Vault.org_id == org_id, Vault.collection_id.is_(None),
                                    Vault.is_deleted == False)
    else:
        # Personal vault only — exclude org-shared entries this user authored.
        query = select(Vault).where(Vault.user_id == user_id,
                                    Vault.org_id.is_(None), Vault.is_deleted == False)

    if category:
        query = query.where(Vault.category == category)

    if cursor:
        data = json.loads(base64.b64decode(cursor))
        cursor_time = datetime.fromisoformat(data["created_at"])
        cursor_id = UUID(data["id"])
        query = query.where(
            or_(
                Vault.created_at > cursor_time,
                and_(Vault.created_at == cursor_time, Vault.id > cursor_id)
            )   
        )

    query = query.order_by(Vault.created_at.asc(), Vault.id.asc()).limit(limit + 1)
    
    result = await db.execute(query)
    vaults = result.scalars().all()
    
    has_next = len(vaults) > limit
    items = list(vaults[:limit])

    next_cursor = None
    if has_next:
        last = items[-1]
        next_cursor = base64.b64encode(json.dumps({
            "created_at": last.created_at.isoformat(),
            "id": str(last.id)
        }).encode()).decode()

    vault_operations_total.labels("read").inc()
    return items, next_cursor, has_next

async def create_vault(db,user_id,data):

    org_id = getattr(data, "org_id", None)
    collection_id = getattr(data, "collection_id", None)
    if collection_id is not None:
        await _require_collection_access(db, collection_id, user_id, write=True)
        # Derive org_id from the collection so it can't be spoofed.
        coll = (await db.execute(
            select(Collection).where(Collection.id == collection_id))).scalar_one()
        org_id = coll.org_id
    elif org_id is not None:
        await _require_member(db, org_id, user_id, write=True)

    vault = Vault(
        user_id = user_id,
        org_id = org_id,
        collection_id = collection_id,
        encrypted = data.encrypted,
        iv = data.iv,
        expires_at = data.expires_at,
        category = data.category
    )
    count = await get_vault_count(db,user_id,org_id,collection_id)
    if count >= 1000:
        raise HTTPException(status_code=400, detail="Vault limit reached (max 1000 entries)")

    db.add(vault)
    await db.commit()
    await db.refresh(vault)
    vault_operations_total.labels("create").inc()
    return vault

async def update_vault(db, user_id, vault_id, data):
    result = await db.execute(select(Vault).where(Vault.id == vault_id))
    vault = result.scalar_one_or_none()

    if vault is None:
        logger.error("Vault not found with provided ID")
        raise HTTPException(status_code=404, detail="Not Found")

    await _authorize_vault(db, vault, user_id, write=True)

    history = VaultHistory(
        vault_id=vault.id,
        encrypted=vault.encrypted,
        iv=vault.iv
    )
    db.add(history)

    # Keep the full change history (no trimming).

    vault.encrypted = data.encrypted
    vault.iv = data.iv
    vault.updated_at = datetime.now()
    vault.expires_at = data.expires_at
    vault.category = data.category
    await db.commit()
    await db.refresh(vault)
    vault_operations_total.labels("update").inc()
    return vault



async def set_pin(db, user_id, vault_id, pinned):
    result = await db.execute(select(Vault).where(Vault.id == vault_id))
    vault = result.scalar_one_or_none()

    if vault is None:
        raise HTTPException(status_code=404, detail="Not Found")
    await _authorize_vault(db, vault, user_id, write=True)

    vault.pinned = pinned
    await db.commit()
    await db.refresh(vault)
    return vault


async def delete_vault(db,user_id,vault_id):

    result = await db.execute(select(Vault).where(Vault.id == vault_id))
    vault = result.scalar_one_or_none()

    if vault is None:
        logger.error("Vault not found")
        raise HTTPException(status_code=404,detail="Not Found")

    await _authorize_vault(db, vault, user_id, write=True)

    vault.is_deleted = True
    await db.commit()
    vault_operations_total.labels("delete").inc()
    return {"message":"deleted"}

async def export_vaults(db,user_id):
    result = await db.execute(
        select(Vault).where(Vault.user_id == user_id)
    )
    vaults = result.scalars().all()

    vault_operations_total.labels("read").inc()

    return vaults

async def import_vaults(db,user_id,entries):
    
    
    count = await get_vault_count(db,user_id)
    if count + len(entries) >= 1000:
        raise HTTPException(status_code=400,detail="Import would exceed vault limit")
    
    vaults = []
    for entry in entries:
        vault = Vault(
            user_id = user_id,
            encrypted = entry.encrypted,
            iv = entry.iv,
            expires_at = entry.expires_at,
            category = entry.category
        )
        db.add(vault)
        vaults.append(vault)

    await db.commit()
    vault_operations_total.labels("create").inc()
    return len(vaults)

async def get_vault_count(db, user_id, org_id=None, collection_id=None):
    query = select(func.count()).select_from(Vault)
    if collection_id is not None:
        query = query.where(Vault.collection_id == collection_id)
    elif org_id is not None:
        query = query.where(Vault.org_id == org_id, Vault.collection_id.is_(None))
    else:
        query = query.where(Vault.user_id == user_id, Vault.org_id.is_(None))
    result = await db.execute(query)
    return result.scalar()



async def  get_vault_history(db,user_id,vault_id):
    result = await db.execute(select(Vault).where(Vault.id == vault_id))
    vault = result.scalar_one_or_none()

    if vault is None:
        raise HTTPException(status_code=404,detail="Not found")
    await _authorize_vault(db, vault, user_id, write=False)

    history = await db.execute(
        select(VaultHistory).where(VaultHistory.vault_id == vault_id)
        .order_by(VaultHistory.changed_at.desc())
    )

    return history.scalars().all()


async def restore_vault(db,user_id,vault_id,history_id):
    result = await db.execute(select(Vault).where(Vault.id == vault_id))
    vault = result.scalar_one_or_none()

    if vault is None:
        raise HTTPException(status_code=404,detail="not found")
    await _authorize_vault(db, vault, user_id, write=True)

    history_result = await db.execute(
        select(VaultHistory).where(VaultHistory.id == history_id,
                                   VaultHistory.vault_id == vault_id)
    )

    history = history_result.scalar_one_or_none()

    if history is None:
        raise HTTPException(status_code=404,detail="History record not found")
    
    vault.encrypted = history.encrypted
    vault.iv = history.iv
    vault.updated_at = datetime.now()
    vault.is_deleted = False
    await db.commit()
    await db.refresh(vault)
    return vault
