from argon2 import PasswordHasher
from sqlalchemy import select
import logging
from jose import jwt
from datetime import datetime,timedelta
from fastapi import HTTPException
from app.models.models import User,RefreshToken
from app.config import settings
from argon2.exceptions import VerifyMismatchError
import secrets
import pyotp
import qrcode
import io
import base64

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


async def login_user(db,redis,email,password):

    failed = await redis.get(f"failed_login:{email}")

    if failed is not None and int(failed) >= 10:
        raise HTTPException(status_code=429,detail="Account temporarily locked")

    result = await db.execute(select(User).where(User.email == email))
    user = result.scalar_one_or_none()

    if user is None:
        logger.error("Failed login attempt for email: %s",email)
        raise HTTPException(status_code=401,detail="User with provided email not found")
    
    if user.is_blocked:
        raise HTTPException(status_code=403, detail="Account has been blocked")
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
    except VerifyMismatchError:
        await redis.incr(f"failed_login:{email}")
        await redis.expire(f"failed_login:{email}",900)
        raise HTTPException(status_code=401,detail="Invalid credentials")
    except Exception as e:
        logger.error("Verification error: %s",e)
        raise HTTPException(status_code=500, detail="Internal server error")
    
    await redis.delete(f"failed_login:{email}")
    await redis.setex(f"refresh:{refresh_token}",604800,str(user.id))

    if user.totp_enabled:
        pending_token = secrets.token_hex(32)
        await redis.setex(f"2fa_pending:{pending_token}",300,str(user.id))
        return {"requires_2fa":True,
                "pending_token":pending_token}
    return {"access_token" : jwt_token,
            "refresh_token": refresh_token, 
            "salt" : user.salt,
            "user_id": str(user.id)}


async def refresh_access_token(db,token,redis):

    cached_user_id = await redis.get(f"refresh:{token}")
    if cached_user_id:
        payload = {
            "sub": cached_user_id,
            "exp": datetime.now() + timedelta(minutes=15)
        }

        return {"access_token": jwt.encode(payload,settings.JWT_SECRET,algorithm="HS256")}

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
    

async def logout(db,redis,token,access_token):
    
    result = await db.execute(select(RefreshToken).where(RefreshToken.token ==token)) 

    token_db = result.scalar_one_or_none()

    if token_db is None:
        logger.error("RefreshToken not found")
        raise HTTPException(status_code=401,detail="Token Error")
    

    await db.delete(token_db)
    await db.commit()
    await redis.delete(f"refresh:{token}")

    await redis.setex(
        f"blacklist:{access_token}",
        900,
        "1"
    )

    return {"message" : "logged out"}


async def get_salt(db,email,redis):
    cached = await redis.get(f"salt:{email}")

    if cached:
        return cached
    
    result = await db.execute(select(User).where(User.email == email))
    user = result.scalar_one_or_none()

    if user is None:
        raise HTTPException(status_code=404,detail="Not found")
    
    await redis.setex(f"salt:{email}",3600,user.salt)
    return user.salt


async def setup_2fa(db,user_id):
    result = await db.execute(select(User).where(User.id == user_id))

    user = result.scalar_one_or_none()

    if user is None:
        raise HTTPException(status_code=404, detail="User not found")
    if user.totp_enabled:
        raise HTTPException(status_code=400,detail="2FA already enabled")
    secret = pyotp.random_base32()
    uri = pyotp.totp.TOTP(secret).provisioning_uri(user.email,issuer_name ="PasswordManager")

    qr = qrcode.make(uri)
    buffer = io.BytesIO()
    qr.save(buffer,format="PNG")
    qr_base = base64.b64encode(buffer.getvalue()).decode()

    user.totp_secret = secret
    await db.commit()

    return {"secret": secret, "qr_code":qr_base}



async def verify_2fa_setup(db,user_id,code):
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()

    if user is None:
        raise HTTPException(status_code=404,detail="User not found")
    
    if not user.totp_secret:
        raise HTTPException(status_code=400,detail="2FA not set up")
    
    if not pyotp.TOTP(user.totp_secret).verify(code):
        raise HTTPException(status_code=401,detail="Invalid TOTP code")
    
    user.totp_enabled = True
    await db.commit()

    return {"message": "2FA enabled"}

async def disable_2fa(db,user_id,code):
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()

    if user is None:
        raise HTTPException(status_code=404,detail="User not found")

    if not user.totp_enabled:                                                            
          raise HTTPException(status_code=400, detail="2FA not enabled")
                                                                                           
    if not pyotp.TOTP(user.totp_secret).verify(code):
        raise HTTPException(status_code=401, detail="Invalid TOTP code")
                                                                                        
    user.totp_secret = None
    user.totp_enabled = False                                                            
    await db.commit()
    return {"message":"2FA disabled"}

async def validate_2fa_code(db,redis,pending_token,code):
    user_id = await redis.get(f"2fa_pending:{pending_token}")
    
    if user_id is None:
        raise HTTPException(status_code=401,detail="Invalid or expired token")
    

    result = await db.execute(select(User).where(User.id == user_id))

    user = result.scalar_one_or_none()

    if user is None:
        raise HTTPException(status_code=404,detail="User not found")
    
    
    if not pyotp.TOTP(user.totp_secret).verify(code):
        raise HTTPException(status_code=401,detail="Invalid TOTP code")
    

    await redis.delete(f"2fa_pending:{pending_token}")

    payload = {
        "sub":str(user.id),
        "exp": datetime.now() + timedelta(minutes=15)
    }

    jwt_token = jwt.encode(payload,settings.JWT_SECRET,algorithm="HS256")
    refresh_token = secrets.token_hex(32)

    refresh_token_record = RefreshToken(
        user_id= user.id,
        token = refresh_token,
        expires_at = datetime.now() + timedelta(days=7)
    )

    db.add(refresh_token_record)
    await db.commit()

    await redis.setex(f"refresh:{refresh_token}",604800,str(user.id))

    return {
        "access_token":jwt_token,
        "refresh_token":refresh_token,
        "salt": user.salt,
        "user_id": str(user.id),
        "email": user.email
    }