from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse



class RequestSizeLimitMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request, call_next):
        max_size = 1024 * 1024
        content_length = request.headers.get("content_lenght")
        if content_length and int(content_length) > max_size:
            return JSONResponse(
                status_code=413,
                content={"detail":"Request too large"}
            )
        

        return await call_next(request)