from fastapi import Request,Response
from app.redis_client import get_redis
import logging

logger = logging.getLogger(__name__)


LIMITS = {
    "/auth/login": 5,
    "/auth/register": 3
}
WINDOW = 60


async def rate_limit_middleware(request: Request,call_next):

    path = request.url.path

    if path not in LIMITS:
        return await call_next(request)
    
    limit = LIMITS[path]
    ip = request.client.host
    key = f"rate_limit:{ip}:{path}"

    async for redis in get_redis():
        count = await redis.incr(key)

        if count == 1:
            await redis.expire(key,WINDOW)

        ttl = await redis.ttl(key)
        remaining = max(0,limit - count)

        if count > limit:
            logger.warning(f"Rate limit exceeded: {ip} on {path}")
            return Response(
                status_code=429,
                headers={
                    "Retry-After": str(ttl),
                    "X-RateLimit-Limit":str(limit),
                    "X-RateLimit-Remaining":"0",
                    "X-RateLimit-Reset":str(ttl)
                }
            )   
        
    response = await call_next(request)
    response.headers["X-RateLimit-Limit"] = str(limit)
    response.headers["X-RateLimit-Remaining"] = str(remaining)                           
    response.headers["X-RateLimit-Reset"] = str(ttl)
    return response




