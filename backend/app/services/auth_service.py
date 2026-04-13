from argon2 import PasswordHasher
from sqlalchemy import select
import logging
from jose import jwt
from datetime import datetime,timedelta
from fastapi import HTTPException
from app.models.models import User
from app.config import settings
from argon2.exceptions import VerifyMismatchError
logger = logging.getLogger(__name__)
ph = PasswordHasher(time_cost = settings.ARGON2_TIME_COST,
                    memory_cost= settings.ARGON2_MEMORY_COST)



async def register_user(db,email,password,salt):
    
    result = await db.execute(select(User).where(User.email == email))

    user = result.scalar_one_or_none()

    if user is not None:
        logger.error("User with that email already exists")
        raise HTTPException(status_code=400, detail="Invalid credentials")

    hashed_password = ph.hash(password)
    user = User(
        email = email,
        password = hashed_password,
        salt = salt

    )

    try:
        db.add(user)
        await db.commit()
        await db.refresh(user)
    except Exception as e:
        await db.rollback()
        logger.error("Database error: %s",e)
        raise HTTPException(status_code=500,detail="Database error")


async def login_user(db,email,password):
    result = await db.execute(select(User).where(User.email == email))

    user = result.scalar_one_or_none()

    if user is None:
        logger.error("Failed login attempt for email: %s",email)
        raise HTTPException(status_code=401,detail="User with provided email not found")
    

    try:
        ph.verify(user.password,password)
        logger.info("Password match, generating JWT")
        payload = {
            "sub" : str(user.id),
            "exp" : datetime.now() + timedelta(minutes=15)
        }
        jwt_token = jwt.encode(payload,settings.JWT_SECRET,algorithm="HS256")

        return {"access_token" : jwt_token, "salt" : user.salt}
    
    except VerifyMismatchError:
        raise HTTPException(status_code=401,detail="Invalid credentials")
    except Exception as e:
        logger.error("Verification error: %s",e)
        raise HTTPException(status_code=500, detail="Internal server error")

