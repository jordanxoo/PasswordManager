import httpx
from fastapi import HTTPException
from app.config import settings


PWNED_PASSWORDS_URL = "https://api.pwnedpasswords.com/range/{}"
BREACHED_ACCOUNT_URL = "https://haveibeenpwned.com/api/v3/breachedaccount/{}"


async def check_password_range(hash_prefix: str) -> list[dict]:
    if len(hash_prefix) != 5 or not hash_prefix.isalnum():
        raise HTTPException(status_code=400,detail="hash_prefix must be " \
        "exactly 5 alphanumeric characters")

    hash_prefix = hash_prefix.upper()

    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(
                PWNED_PASSWORDS_URL.format(hash_prefix),
                timeout=5.0
            )

        except httpx.TimeoutException:
            raise HTTPException(status_code=503,detail="HIBP service timeout")
        
        except httpx.RequestError:
            raise HTTPException(status_code=503,detail="HIBP service unavailable")
        
        if response.status_code == 429:
            raise HTTPException(status_code=429,detail="HIBP rate limit exceeded,try again later")
        
        if response.status_code != 200:
            raise HTTPException(status_code=502,detail="HIBP service error")
        

        results = []
        for line in response.text.splitlines():
            suffix, count = line.split(":")
            results.append({"suffix": suffix,"count":int(count)})
      
        return results
    

async def check_email_breach(email:str) -> list[dict]:
    api_key = getattr(settings,"HIBP_API_KEY",None)

    if not api_key:
        raise HTTPException(status_code=501,detail="Email breach check not configured " \
        "(HIBP_API_KEY missing)")
    

    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(
                BREACHED_ACCOUNT_URL.format(email),
                headers=
                {
                    "hibp-api-key": api_key,
                    "user-agent": "PasswordManager-App"
                },
                timeout=5.0
            )

        except httpx.TimeoutException:
            raise HTTPException(status_code=503, detail="HIBP service timeout")
        
        except httpx.RequestError:
            raise HTTPException(status_code=503,detail="HIBP service unavailable")
        
        if response.status_code == 404:
            return []
        
        if response.status_code == 401:
            raise HTTPException(status_code=502,detail="Invalid HIBP API key")
        
        if response.status_code == 429:
            raise HTTPException(status_code=429,detail="HIBP rate limit exceeded,try again later")
        
        if response.status_code != 200:
            raise HTTPException(status_code=502, detail="HIBP service error")
        
        return [
            {"name":b["Name"],"breach_date":b["BreachDate"],"pwn_count": b["PwnCount"]}
            for b in response.json()
        ]