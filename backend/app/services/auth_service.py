from argon2 import PasswordHasher
from sqlalchemy import select,delete
import logging
from jose import jwt
from datetime import datetime,timedelta
from fastapi import HTTPException
from app.models.models import User,RefreshToken
from app.config import settings
from argon2.exceptions import VerifyMismatchError
import secrets
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
        refresh_token = secrets.token_hex(32)

        refresh_token_record = RefreshToken(
            user_id = user.id,
            token= refresh_token,
            expires_at = datetime.now() + timedelta(days=7)
        )

        db.add(refresh_token_record)
        await db.commit()


        return {"access_token" : jwt_token,
                "refresh_token": refresh_token, 
                "salt" : user.salt}
    
    except VerifyMismatchError:
        raise HTTPException(status_code=401,detail="Invalid credentials")
    except Exception as e:
        logger.error("Verification error: %s",e)
        raise HTTPException(status_code=500, detail="Internal server error")


async def refresh_access_token(db,token):

    result = await db.execute(select(RefreshToken).where(RefreshToken.token == token))

    token_db = result.scalar_one_or_none()

    if token_db is None:
        logger.error("RefreshToken not found")
        raise HTTPException(status_code=401,detail="Token Error")
    
    if token_db.expires_at < datetime.now():
        raise HTTPException(status_code=401,detail="Refresh token expired")



    payload = {
        "sub": str(token_db.user_id),
        "exp": datetime.now() + timedelta(minutes=15)
    }
    new_jwt = jwt.encode(payload,settings.JWT_SECRET,algorithm="HS256")

    return {"access_token" : new_jwt}
    

async def logout(db, token):
    
    result = await db.execute(select(RefreshToken).where(RefreshToken.token ==token)) 

    token_db = result.scalar_one_or_none()

    if token_db is None:
        logger.error("RefreshToken not found")
        raise HTTPException(status_code=401,detail="Token Error")
    

    await db.delete(token_db)
    await db.commit()

    return {"message" : "logged out"}