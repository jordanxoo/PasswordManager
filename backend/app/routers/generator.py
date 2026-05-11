import secrets
import math
from fastapi import APIRouter,Depends,HTTPException,Query
from app.dependencies import get_current_user

router = APIRouter()

UPPERCASE = "ABCDEFGHIJKLMNOPQRSTUVWXYZ"
LOWERCASE = "abcdefghijklmnopqrstuvwxyz"
NUMBERS   = "0123456789"
SYMBOLS   = "!@#$%^&*()-_=+[]{}|;:,.<>?"
AMBIGUOUS = set("0O1lI")

@router.get("/")
async def generate_password(
    length:             int  = Query(default=16, ge=8, le=128),
    uppercase:          bool = Query(default=True),
    lowercase:          bool = Query(default=True),
    numbers:            bool = Query(default=True),
    symbols:            bool = Query(default=True),
    exclude_ambiguous:  bool = Query(default=False),
    user_id:            str  = Depends(get_current_user)
):
    def clean(chars):
        if exclude_ambiguous:
            return "".join(c for c in chars if c not in AMBIGUOUS)
        return chars
    
    groups = []
    if uppercase: groups.append(clean(UPPERCASE))
    if lowercase: groups.append(clean(LOWERCASE))
    if numbers: groups.append(clean(NUMBERS))
    if symbols: groups.append(clean(SYMBOLS))

    if not groups: 
        raise HTTPException(status_code=400, detail="At least one character set must be selected")
    
    alphabet = "".join(groups)

    guaranteed = [secrets.choice(g) for g in groups]
    remaining = [secrets.choice(alphabet) for _ in range(length-len(guaranteed))]

    password_chars = guaranteed + remaining
    secrets.SystemRandom().shuffle(password_chars)
    password = "".join(password_chars)
    entropy = round(length * math.log2(len(alphabet)),1)

    return {"password": password, "length": length, "entropy": entropy}

