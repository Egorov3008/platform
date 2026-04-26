from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse
from app.core.config import settings

_EXEMPT_PREFIXES = (
    "/api/v1/auth/",
    "/api/v1/bot/",
)
_EXEMPT_EXACT = {"/api/v1/payments/webhook"}
_SAFE_METHODS = frozenset({"GET", "HEAD", "OPTIONS"})


class CSRFMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        if not settings.csrf_enabled:
            return await call_next(request)
        if request.method in _SAFE_METHODS:
            return await call_next(request)
        path = request.url.path
        if path in _EXEMPT_EXACT:
            return await call_next(request)
        for prefix in _EXEMPT_PREFIXES:
            if path.startswith(prefix):
                return await call_next(request)
        csrf_cookie = request.cookies.get("csrf_token")
        csrf_header = request.headers.get("X-CSRF-Token")
        if not csrf_cookie or csrf_cookie != csrf_header:
            return JSONResponse(
                status_code=403,
                content={"detail": "CSRF validation failed"},
            )
        return await call_next(request)
