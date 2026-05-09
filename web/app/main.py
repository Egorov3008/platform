from contextlib import asynccontextmanager
from pathlib import Path
from fastapi import FastAPI, Request
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from starlette.middleware.base import BaseHTTPMiddleware
import httpx
from app.core.database import create_pool, close_pool, get_pool
from app.core.logging import setup_logging, get_logger
from app.core.csrf import CSRFMiddleware
from app.api import auth, keys, tariffs, payments, admin, users
from app.core.config import settings
from app.core.dependencies import set_backend_http_client


class NoCacheJSMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        response = await call_next(request)
        if request.url.path.endswith('.js'):
            response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
        return response


class CSPMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        response = await call_next(request)
        # Allow Telegram Widget iframe and scripts
        # Note: frame-src controls what iframes CAN be embedded IN this page
        response.headers["Content-Security-Policy"] = (
            "default-src 'self'; "
            "script-src 'self' 'unsafe-eval' https://telegram.org https://oauth.telegram.org; "
            "frame-src https://oauth.telegram.org; "
            "style-src 'self' 'unsafe-inline' https://fonts.googleapis.com; "
            "font-src 'self' https://fonts.gstatic.com; "
            "img-src 'self' https: data:; "
            "connect-src 'self' https://oauth.telegram.org https://api.telegram.org"
        )
        return response

setup_logging(
    log_level=settings.log_level,
    log_file=settings.log_file or None,
    log_format=settings.log_format,
)

logger = get_logger(__name__)

FRONTEND_DIR = Path(__file__).resolve().parent.parent / "frontend"


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Запуск приложения VPN Web Backend")

    # Initialize backend HTTP client
    backend_base_url = settings.backend_url
    if settings.use_host_backend and backend_base_url.startswith("http://backend"):
        backend_base_url = backend_base_url.replace("http://backend", "http://host.docker.internal")
    backend_client = httpx.AsyncClient(base_url=backend_base_url, timeout=30.0, follow_redirects=True)
    set_backend_http_client(backend_client)
    logger.info(f"Backend HTTP client initialized: {backend_base_url}")

    # Initialize auth DB pool (login_codes, web_users)
    await create_pool()
    logger.info("Подключение к базе данных установлено")

    yield

    # Cleanup: close backend client before closing database pool
    await backend_client.aclose()
    logger.info("Backend HTTP client closed")

    await close_pool()
    logger.info("Приложение завершает работу")


app = FastAPI(title="VPN Web Backend", version="1.0.0", lifespan=lifespan)

app.add_middleware(NoCacheJSMiddleware)
app.add_middleware(CSPMiddleware)
app.add_middleware(CSRFMiddleware)

app.include_router(auth.router, prefix="/api/v1/auth", tags=["auth"])
app.include_router(keys.router, prefix="/api/v1/keys", tags=["keys"])
app.include_router(tariffs.router, prefix="/api/v1/tariffs", tags=["tariffs"])
app.include_router(payments.router, prefix="/api/v1/payments", tags=["payments"])
app.include_router(admin.router, prefix="/api/v1/admin", tags=["admin"])
app.include_router(users.router, prefix="/api/v1/users", tags=["users"])


@app.get("/health")
async def health():
    return {"status": "ok"}


@app.get("/")
async def serve_frontend():
    return FileResponse(FRONTEND_DIR / "index.html")


app.mount("/", StaticFiles(directory=str(FRONTEND_DIR)), name="frontend")
