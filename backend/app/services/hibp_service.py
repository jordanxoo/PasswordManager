import httpx
import json
from fastapi import HTTPException
from app.config import settings
from app.metrics import hibp_cache_hits_total,hibp_cache_misses_total
PWNED_PASSWORDS_URL = "https://api.pwnedpasswords.com/range/{}"
BREACHED_ACCOUNT_URL = "https://haveibeenpwned.com/api/v3/breachedaccount/{}"
RATE_LIMIT_MAX = 10
RATE_LIMIT_WINDOW = 60


async def check_rate_limit(redis, user_id: str):
    key = f"hibp:ratelimit:{user_id}"
    count = await redis.incr(key)
    if count == 1:
        await redis.expire(key, RATE_LIMIT_WINDOW)
    if count > RATE_LIMIT_MAX:
        ttl = await redis.ttl(key)
        raise HTTPException(
            status_code=429,
            detail=f"Too many HIBP requests. Try again in {ttl} seconds."
        )


async def check_password_range(hash_prefix: str, redis) -> list[dict]:
    if len(hash_prefix) != 5 or not hash_prefix.isalnum():
        raise HTTPException(status_code=400, detail="hash_prefix must be exactly 5 alphanumeric characters")

    hash_prefix = hash_prefix.upper()
    cache_key = f"hibp:range:{hash_prefix}"

    cached = await redis.get(cache_key)
    if cached:
        hibp_cache_hits_total.inc()
        return json.loads(cached)

    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(
                PWNED_PASSWORDS_URL.format(hash_prefix),
                timeout=5.0
            )
        except httpx.TimeoutException:
            raise HTTPException(status_code=503, detail="HIBP service timeout")
        except httpx.RequestError:
            raise HTTPException(status_code=503, detail="HIBP service unavailable")

    if response.status_code == 429:
        raise HTTPException(status_code=429, detail="HIBP rate limit exceeded, try again later")
    if response.status_code != 200:
        raise HTTPException(status_code=502, detail="HIBP service error")

    results = []
    for line in response.text.splitlines():
        suffix, count = line.split(":")
        results.append({"suffix": suffix, "count": int(count)})
    hibp_cache_misses_total.inc()
    await redis.setex(cache_key, 86400, json.dumps(results))
    return results


async def check_email_breach(email: str) -> list[dict]:
    api_key = getattr(settings, "HIBP_API_KEY", None)
    if not api_key:
        raise HTTPException(status_code=501, detail="Email breach check not configured(HIBP_API_KEY missing)")

    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(
                BREACHED_ACCOUNT_URL.format(email),
                headers={"hibp-api-key": api_key, "user-agent": "PasswordManager-App"},
                timeout=5.0
            )
        except httpx.TimeoutException:
            raise HTTPException(status_code=503, detail="HIBP service timeout")
        except httpx.RequestError:
            raise HTTPException(status_code=503, detail="HIBP service unavailable")

    if response.status_code == 404:
        return []
    if response.status_code == 401:
        raise HTTPException(status_code=502, detail="Invalid HIBP API key")
    if response.status_code == 429:
        raise HTTPException(status_code=429, detail="HIBP rate limit exceeded, try again later")
    if response.status_code != 200:
        raise HTTPException(status_code=502, detail="HIBP service error")

    return [
        {"name": b["Name"], "breach_date": b["BreachDate"], "pwn_count": b["PwnCount"]}
        for b in response.json()]

