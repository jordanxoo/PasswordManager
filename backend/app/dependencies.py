from fastapi import Depends, HTTPException, Header
from fastapi.security import OAuth2PasswordBearer
from jose import jwt
from jose.exceptions import JWTError
from app.config import settings
import logging
from sqlalchemy.ext.asyncio import AsyncSession
from app.database import get_db
from app.redis_client import get_redis
from app.models import User
from sqlalchemy import select
from app.models.enums import Role
from dataclasses import dataclass

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")
logger = logging.getLogger(__name__)


@dataclass
class AuthContext:
    user_id: str
    scope: str


async def get_current_user(token: str = Depends(oauth2_scheme),
                            db: AsyncSession = Depends(get_db),
                            redis=Depends(get_redis)):
    try:
        payload = jwt.decode(token, settings.JWT_SECRET, algorithms=["HS256"])
        user_id = payload.get("sub")
        if user_id is None:
            raise HTTPException(401, detail="Unauthorized")
        is_blacklisted = await redis.get(f"blacklist:{token}")
        if is_blacklisted:
            raise HTTPException(status_code=401, detail="Token has been revoked")
        return user_id
    except JWTError as e:
        logger.error("Error with JWT: %s", e)
        raise HTTPException(status_code=401, detail="Invalid Token")


async def get_auth_context(
    authorization: str | None = Header(default=None),
    x_api_key: str | None = Header(default=None),
    db: AsyncSession = Depends(get_db),
    redis=Depends(get_redis)) -> AuthContext:
    if authorization and authorization.startswith("Bearer "):
        token = authorization[7:]
        try:
            payload = jwt.decode(token, settings.JWT_SECRET,algorithms=["HS256"])
            user_id = payload.get("sub")
            if user_id is None:
                raise HTTPException(status_code=401, detail="Unauthorized")
            is_blacklisted = await redis.get(f"blacklist:{token}")
            if is_blacklisted:
                raise HTTPException(status_code=401, detail="Token has been revoked")
            return AuthContext(user_id=user_id, scope="write")
        except JWTError:
            raise HTTPException(status_code=401, detail="Invalid token")

    if x_api_key:
        from app.services.api_key_service import verify_api_key
        result = await verify_api_key(db, x_api_key)
        if result is None:
            raise HTTPException(status_code=401, detail="Invalid or expired API key")
        user_id, scope = result
        return AuthContext(user_id=user_id, scope=scope)

    raise HTTPException(status_code=401, detail="Not authenticated")


async def require_read(auth: AuthContext = Depends(get_auth_context)) -> str:
    return auth.user_id


async def require_write(auth: AuthContext = Depends(get_auth_context)) -> str:
    if auth.scope == "read":
        raise HTTPException(status_code=403, detail="Read-only API key cannot perform this action")
    return auth.user_id


async def require_admin(user_id: str = Depends(get_current_user),
                        db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if user is None or user.role != Role.ADMIN:
        raise HTTPException(status_code=403, detail="Admin access required")
    return user_id


def require_org_role(min_role):
    """Dependency factory enforcing organization membership + a minimum role.

    Resolves the `org_id` path param, loads the current user's membership and
    checks it against the role hierarchy. Returns the membership on success."""
    from app.models.enums import OrgRole
    from app.services.organization_service import ROLE_RANK

    async def dependency(org_id,
                         user_id: str = Depends(get_current_user),
                         db: AsyncSession = Depends(get_db)):
        from app.services.organization_service import get_membership
        membership = await get_membership(db, org_id, user_id)
        if membership is None:
            raise HTTPException(status_code=403, detail="Not a member of this organization")
        if ROLE_RANK[membership.role] < ROLE_RANK[min_role]:
            raise HTTPException(status_code=403, detail="Insufficient permissions")
        return membership

    return dependency