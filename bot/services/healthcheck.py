"""
Health check сервис для мониторинга состояния приложения.

Предоставляет endpoint /health для проверки работоспособности бота.
"""

import asyncio
import time
from typing import Dict, Any, Optional

from aiohttp import web

from logger import logger


class HealthCheckService:
    """Сервис проверки состояния приложения"""

    def __init__(
        self,
        db_pool: Optional[Any] = None,
        cache_service: Optional[Any] = None,
        xui_session: Optional[Any] = None,
    ):
        self.db_pool = db_pool
        self.cache_service = cache_service
        self.xui_session = xui_session
        self._startup_time = time.time()
        self._last_successful_check: Dict[str, float] = {}
    
    async def check_database(self) -> Dict[str, Any]:
        """Проверка подключения к базе данных"""
        start = time.monotonic()
        try:
            if not self.db_pool:
                return {
                    "status": "error",
                    "message": "DB pool not initialized",
                    "latency_ms": 0,
                }
            
            async with self.db_pool.acquire() as conn:
                await conn.fetchval("SELECT 1")
            
            latency = (time.monotonic() - start) * 1000
            self._last_successful_check["database"] = time.time()
            
            return {
                "status": "ok",
                "latency_ms": round(latency, 2),
            }
        except Exception as e:
            logger.error(
                "Health check: database error",
                error_type=type(e).__name__,
                error_message=str(e)
            )
            return {
                "status": "error",
                "message": str(e),
                "latency_ms": round((time.monotonic() - start) * 1000, 2),
            }
    
    async def check_cache(self) -> Dict[str, Any]:
        """Проверка подключения к кэшу (Redis)"""
        start = time.monotonic()
        try:
            if not self.cache_service:
                return {
                    "status": "skipped",
                    "message": "Cache service not provided",
                }
            
            # Проверка через ping
            if hasattr(self.cache_service, "ping"):
                result = await self.cache_service.ping()
                if result:
                    self._last_successful_check["cache"] = time.time()
                    return {"status": "ok"}
                else:
                    return {"status": "error", "message": "Ping failed"}
            else:
                # Альтернативная проверка
                self._last_successful_check["cache"] = time.time()
                return {"status": "ok", "message": "Cache service available"}
                
        except Exception as e:
            logger.error(
                "Health check: cache error",
                error_type=type(e).__name__,
                error_message=str(e)
            )
            return {
                "status": "error",
                "message": str(e),
                "latency_ms": round((time.monotonic() - start) * 1000, 2),
            }
    
    async def check_xui_api(self) -> Dict[str, Any]:
        """Проверка подключения к XUI API"""
        start = time.monotonic()
        try:
            if not self.xui_session:
                return {
                    "status": "skipped",
                    "message": "XUI session not provided",
                }
            
            # Простая проверка — получение списка inbounds
            inbounds = await self.xui_session.get_inbounds()
            
            self._last_successful_check["xui_api"] = time.time()
            return {
                "status": "ok",
                "inbounds_count": len(inbounds) if inbounds else 0,
                "latency_ms": round((time.monotonic() - start) * 1000, 2),
            }
        except Exception as e:
            logger.error(
                "Health check: XUI API error",
                error_type=type(e).__name__,
                error_message=str(e)
            )
            return {
                "status": "error",
                "message": str(e),
                "latency_ms": round((time.monotonic() - start) * 1000, 2),
            }
    
    async def get_full_health(self) -> Dict[str, Any]:
        """Полная проверка всех компонентов"""
        db_result = await self.check_database()
        cache_result = await self.check_cache()
        xui_result = await self.check_xui_api()
        
        # Определяем общий статус
        components = {
            "database": db_result,
            "cache": cache_result,
            "xui_api": xui_result,
        }
        
        errors = [
            comp for comp in components.values()
            if comp.get("status") == "error"
        ]
        
        overall_status = "unhealthy" if errors else "healthy"
        
        uptime = time.time() - self._startup_time
        
        return {
            "status": overall_status,
            "timestamp": time.time(),
            "uptime_seconds": round(uptime, 2),
            "components": components,
            "last_successful_checks": {
                k: round(time.time() - v, 2) if v else None
                for k, v in self._last_successful_check.items()
            },
        }
    
    async def get_simple_health(self) -> Dict[str, Any]:
        """Быстрая проверка только критических компонентов"""
        db_result = await self.check_database()
        
        return {
            "status": "healthy" if db_result["status"] == "ok" else "unhealthy",
            "database": db_result,
        }


# Глобальный сервис
_health_service: Optional[HealthCheckService] = None


def init_health_service(
    db_pool: Optional[Any] = None,
    cache_service: Optional[Any] = None,
    xui_session: Optional[Any] = None,
) -> HealthCheckService:
    """Инициализирует глобальный health check сервис"""
    global _health_service
    _health_service = HealthCheckService(
        db_pool=db_pool,
        cache_service=cache_service,
        xui_session=xui_session,
    )
    logger.info(
        "Health check service initialized",
        has_db=db_pool is not None,
        has_cache=cache_service is not None,
        has_xui=xui_session is not None
    )
    return _health_service


def get_health_service() -> Optional[HealthCheckService]:
    """Получает глобальный health check сервис"""
    return _health_service


# HTTP обработчики для aiohttp
async def health_check_handler(request: web.Request) -> web.Response:
    """
    HTTP обработчик для /health endpoint.
    
    Query параметры:
        - full: если true, возвращает полную проверку всех компонентов
    """
    service = get_health_service()
    if not service:
        return web.json_response(
            {"status": "error", "message": "Health service not initialized"},
            status=503
        )
    
    full = request.query.get("full", "false").lower() == "true"
    
    if full:
        result = await service.get_full_health()
    else:
        result = await service.get_simple_health()
    
    status_code = 200 if result["status"] == "healthy" else 503
    return web.json_response(result, status=status_code)


async def ready_check_handler(request: web.Request) -> web.Response:
    """
    HTTP обработчик для /ready endpoint.
    Проверяет, готов ли бот обрабатывать запросы.
    """
    service = get_health_service()
    if not service:
        return web.json_response(
            {"ready": False, "reason": "Health service not initialized"},
            status=503
        )
    
    result = await service.get_simple_health()
    ready = result["status"] == "healthy"
    
    return web.json_response(
        {"ready": ready, "database": result.get("database", {})},
        status=200 if ready else 503
    )


async def live_check_handler(request: web.Request) -> web.Response:
    """
    HTTP обработчик для /live endpoint.
    Простая проверка — жив ли процесс.
    """
    return web.json_response({"alive": True})
