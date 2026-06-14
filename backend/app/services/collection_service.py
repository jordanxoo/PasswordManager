from sqlalchemy import select, delete
from fastapi import HTTPException
import logging
from app.models.models import Collection, CollectionAccess, Vault, VaultHistory, User

logger = logging.getLogger(__name__)


async def get_collection_access(db, collection_id, user_id):
    """Return the access row for (collection, user) or None."""
    result = await db.execute(
        select(CollectionAccess).where(
            CollectionAccess.collection_id == collection_id,
            CollectionAccess.user_id == user_id,
        )
    )
    return result.scalar_one_or_none()


async def _get_collection_in_org(db, org_id, collection_id):
    coll = (await db.execute(
        select(Collection).where(Collection.id == collection_id))).scalar_one_or_none()
    if coll is None or str(coll.org_id) != str(org_id):
        raise HTTPException(status_code=404, detail="Collection not found")
    return coll


async def create_collection(db, org_id, name, creator_id, wrapped_key):
    coll = Collection(org_id=org_id, name=name)
    db.add(coll)
    await db.flush()  # assign coll.id

    access = CollectionAccess(
        collection_id=coll.id, user_id=creator_id, wrapped_collection_key=wrapped_key)
    db.add(access)
    await db.commit()
    await db.refresh(coll)
    return coll, access


async def list_collections(db, org_id, user_id):
    """Collections in the org the user has access to, each with their wrapped key."""
    result = await db.execute(
        select(Collection, CollectionAccess)
        .join(CollectionAccess, CollectionAccess.collection_id == Collection.id)
        .where(Collection.org_id == org_id, CollectionAccess.user_id == user_id)
        .order_by(Collection.created_at.asc())
    )
    return result.all()


async def list_collection_members(db, org_id, collection_id):
    await _get_collection_in_org(db, org_id, collection_id)
    result = await db.execute(
        select(CollectionAccess, User)
        .join(User, User.id == CollectionAccess.user_id)
        .where(CollectionAccess.collection_id == collection_id)
        .order_by(CollectionAccess.created_at.asc())
    )
    return result.all()


async def grant_access(db, org_id, collection_id, email, wrapped_key):
    await _get_collection_in_org(db, org_id, collection_id)
    user = (await db.execute(select(User).where(User.email == email))).scalar_one_or_none()
    if user is None:
        raise HTTPException(status_code=404, detail="User not found")
    if user.public_key is None:
        raise HTTPException(status_code=400, detail="User has not set up encryption keys yet")
    if await get_collection_access(db, collection_id, user.id) is not None:
        raise HTTPException(status_code=400, detail="User already has access")

    access = CollectionAccess(
        collection_id=collection_id, user_id=user.id, wrapped_collection_key=wrapped_key)
    db.add(access)
    await db.commit()
    await db.refresh(access)
    return access, user


async def revoke_access(db, org_id, collection_id, user_id):
    await _get_collection_in_org(db, org_id, collection_id)
    access = await get_collection_access(db, collection_id, user_id)
    if access is None:
        raise HTTPException(status_code=404, detail="Member has no access to this collection")
    await db.delete(access)
    await db.commit()
    return {"message": "revoked"}


async def rotate_collection_key(db, org_id, collection_id, remove_user_id, member_keys, vault_items):
    """Re-key a collection: new wrapped key for every remaining member with access
    and replaced ciphertext for every item — atomically. Optionally revokes a
    member in the same call. Mirrors organization_service.rotate_org_key."""
    await _get_collection_in_org(db, org_id, collection_id)

    # 1. Optionally revoke a member's access as part of the rotation.
    if remove_user_id is not None:
        target = await get_collection_access(db, collection_id, remove_user_id)
        if target is None:
            raise HTTPException(status_code=404, detail="Member has no access to this collection")
        await db.delete(target)
        await db.flush()

    # 2. New wrapped keys must cover exactly the remaining members with access.
    rows = (await db.execute(
        select(CollectionAccess).where(
            CollectionAccess.collection_id == collection_id))).scalars().all()
    by_user = {str(a.user_id): a for a in rows}
    provided = {str(mk.user_id): mk.wrapped_collection_key for mk in member_keys}
    if set(provided) != set(by_user):
        raise HTTPException(
            status_code=400,
            detail="member_keys must cover exactly the remaining members with access")

    # 3. Re-encrypted items must cover exactly the active collection entries.
    vaults = (await db.execute(
        select(Vault).where(Vault.collection_id == collection_id))).scalars().all()
    active = {str(v.id): v for v in vaults if not v.is_deleted}
    provided_items = {str(i.id): i for i in vault_items}
    if set(provided_items) != set(active):
        raise HTTPException(
            status_code=400,
            detail="vault_items must cover exactly the active collection entries")

    # 4. Apply new wrapped keys + new ciphertext.
    for uid, wrapped in provided.items():
        by_user[uid].wrapped_collection_key = wrapped
    for vid, item in provided_items.items():
        active[vid].encrypted = item.encrypted
        active[vid].iv = item.iv

    # 5. Purge old-key ciphertext: collection-entry history + soft-deleted entries.
    coll_vault_ids = select(Vault.id).where(Vault.collection_id == collection_id)
    await db.execute(delete(VaultHistory).where(VaultHistory.vault_id.in_(coll_vault_ids)))
    await db.execute(delete(Vault).where(Vault.collection_id == collection_id,
                                         Vault.is_deleted == True))
    await db.commit()
    return {"message": "rotated"}


async def delete_collection(db, org_id, collection_id):
    """Delete a collection and everything it owns. FKs lack CASCADE, so children
    go before parents (cf. delete_organization)."""
    await _get_collection_in_org(db, org_id, collection_id)
    coll_vault_ids = select(Vault.id).where(Vault.collection_id == collection_id)
    await db.execute(delete(VaultHistory).where(VaultHistory.vault_id.in_(coll_vault_ids)))
    await db.execute(delete(Vault).where(Vault.collection_id == collection_id))
    await db.execute(delete(CollectionAccess).where(
        CollectionAccess.collection_id == collection_id))
    await db.execute(delete(Collection).where(Collection.id == collection_id))
    await db.commit()
    return {"message": "deleted"}
