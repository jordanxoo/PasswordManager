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
import pyotp
import qrcode
import io
import base64
from urllib.parse import quote, urlencode
from app.metrics import login_failures_total
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
        family_id = secrets.token_hex(16)

        refresh_token_record = RefreshToken(
            user_id = user.id,
            token= refresh_token,
            family_id = family_id,
            expires_at = datetime.now() + timedelta(days=7),
            is_used = False)

        db.add(refresh_token_record)
        await db.commit()
    except VerifyMismatchError:
        await redis.incr(f"failed_login:{email}")
        await redis.expire(f"failed_login:{email}",900)
        login_failures_total.inc()
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


async def refresh_access_token(db, token, redis):
    result = await db.execute(select(RefreshToken).where(RefreshToken.token == token))
    token_db = result.scalar_one_or_none()

    if token_db is None:
        raise HTTPException(status_code=401, detail="Invalid refresh token")
    if token_db.is_used:
        logger.warning("Refresh token reuse detected, invalidating family: %s", token_db.family_id)
        await db.execute(delete(RefreshToken).where(RefreshToken.family_id ==token_db.family_id))
        await db.commit()
        raise HTTPException(status_code=401, detail="Token reuse detected. Please login again.")

    if token_db.expires_at < datetime.now():
        await db.delete(token_db)
        await db.commit()
        raise HTTPException(status_code=401, detail="Refresh token expired")

    token_db.is_used = True

    new_refresh_token = secrets.token_hex(32)
    new_token_record = RefreshToken(
        user_id=token_db.user_id,
        token=new_refresh_token,
        family_id=token_db.family_id,
        expires_at=datetime.now() + timedelta(days=7),
        is_used=False
    )   
    db.add(new_token_record)
    await db.commit()

    await redis.delete(f"refresh:{token}")
    await redis.setex(f"refresh:{new_refresh_token}", 604800, str(token_db.user_id))
    
    payload = {
        "sub": str(token_db.user_id),
        "exp": datetime.now() + timedelta(minutes=15)
    }   

    return {
        "access_token": jwt.encode(payload, settings.JWT_SECRET, algorithm="HS256"),
        "new_refresh_token": new_refresh_token
    }   
    
        

async def logout(db,redis,token,access_token):
    
    result = await db.execute(select(RefreshToken).where(RefreshToken.token ==token)) 

    token_db = result.scalar_one_or_none()

    if token_db is None:
        logger.error("RefreshToken not found")
        raise HTTPException(status_code=401,detail="Token Error")
    

    await db.execute(delete(RefreshToken).where(RefreshToken.family_id == token_db.family_id))

    await db.commit()
    await redis.delete(f"refresh:{token}")

    try:
        payload = jwt.decode(access_token,settings.JWT_SECRET,algorithms=["HS256"])
        remaining = payload["exp"] - int(datetime.now().timestamp())

        if remaining > 0:
            await redis.setex(f"blacklist:{access_token}",remaining,"1")

    except Exception:
        pass
    
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
    # Build the otpauth URI by hand so every TOTP parameter is spelled out in the
    # QR — issuer, account, algorithm, digits, period. pyotp.build_uri strips
    # values equal to the defaults, so we'd otherwise lose digits/period. These
    # MUST match what pyotp.TOTP(secret).verify() uses below (SHA1 / 6 digits / 30s).
    issuer = "PasswordManager"
    label = f"{quote(issuer)}:{quote(user.email)}"
    params = urlencode({
        "secret": secret,
        "issuer": issuer,
        "algorithm": "SHA1",
        "digits": 6,
        "period": 30,
    }).replace("+", "%20")
    uri = f"otpauth://totp/{label}?{params}"

    qr = qrcode.make(uri)
    buffer = io.BytesIO()
    qr.save(buffer,format="PNG")
    qr_base = base64.b64encode(buffer.getvalue()).decode()

    user.totp_secret = secret
    await db.commit()

    return {"secret": secret, "qr_code":qr_base}



async def verify_2fa_setup(db,user_id,code):
    from app.services.recovery_service import generate_recovery_codes
    
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
    codes = await generate_recovery_codes(db,user_id)

    return {"message": "2FA enabled", "recovery_codes":codes}

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
    family_id = secrets.token_hex(16)
    refresh_token_record = RefreshToken(
        user_id= user.id,
        token = refresh_token,
        family_id = family_id,
        expires_at = datetime.now() + timedelta(days=7),
        is_used = False
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