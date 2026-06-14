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
