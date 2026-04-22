from fastapi import Depends,HTTPException
from fastapi.security import OAuth2PasswordBearer
from jose import jwt
from jose.exceptions import JWTError
from app.config import settings
import logging
from sqlalchemy.ext.asyncio import AsyncSession
from app.database import get_db
from app.redis_client import get_redis
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")
logger = logging.getLogger(__name__)

async def get_current_user(token: str = Depends(oauth2_scheme),
                           db: AsyncSession = Depends(get_db),
                           redis = Depends(get_redis)):
    
    try:
        payload = jwt.decode(token,settings.JWT_SECRET,algorithms=["HS256"])
        user_id = payload.get("sub")

        if user_id is None:
            logger.error("User not found")
            raise HTTPException(401,detail="Unauthorized")
        
        is_blacklisted = await redis.get(f"blacklist:{token}")
        if is_blacklisted:
            logger.error("User JWT blacklisted")
            raise HTTPException(status_code=401,detail="Token has been revoked")
        
        return user_id
    
    except JWTError as e:
        logger.error("Error with JWT: %s",e)
        raise HTTPException(status_code=401,detail="Invalid Token")
        