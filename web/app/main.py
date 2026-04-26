from contextlib import asynccontextmanager
from pathlib import Path
from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from app.core.database import create_pool, close_pool, get_pool
from app.core.logging import setup_logging, get_logger
from app.core.csrf import CSRFMiddleware
from app.api import auth, bot, keys, tariffs, payments, admin
from app.core.config import settings
from app.background.scheduler import init_scheduler, add_jobs, shutdown_scheduler

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
    await create_pool()
    logger.info("Подключение к базе данных установлено")

    # Инициализируем и запускаем scheduler для фоновых задач
    init_scheduler()
    pool = get_pool()
    add_jobs(pool)
    logger.info("Фоновые задачи инициализированы")

    yield

    # Останавливаем scheduler при завершении
    shutdown_scheduler()
    await close_pool()
    logger.info("Приложение завершает работу")


app = FastAPI(title="VPN Web Backend", version="1.0.0", lifespan=lifespan)

app.add_middleware(CSRFMiddleware)

app.include_router(auth.router, prefix="/api/v1/auth", tags=["auth"])
app.include_router(bot.router, prefix="/api/v1/bot", tags=["bot"])
app.include_router(keys.router, prefix="/api/v1/keys", tags=["keys"])
app.include_router(tariffs.router, prefix="/api/v1/tariffs", tags=["tariffs"])
app.include_router(payments.router, prefix="/api/v1/payments", tags=["payments"])
app.include_router(admin.router, prefix="/api/v1/admin", tags=["admin"])


@app.get("/health")
async def health():
    return {"status": "ok"}


@app.get("/")
async def serve_frontend():
    return FileResponse(FRONTEND_DIR / "index.html")


app.mount("/", StaticFiles(directory=str(FRONTEND_DIR)), name="frontend")
