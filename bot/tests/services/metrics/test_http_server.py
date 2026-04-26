"""Тесты для HTTP сервера метрик."""

from aiohttp import web
from aiohttp.test_utils import TestClient, TestServer

from services.metrics.http_server import setup_metrics_routes


class TestMetricsRoutes:
    """Тесты для настройки маршрутов."""

    def test_setup_adds_route(self):
        app = web.Application()
        setup_metrics_routes(app)

        routes = [
            r.resource.canonical
            for r in app.router.routes()
            if hasattr(r, "resource") and r.resource
        ]
        assert "/metrics" in routes


async def test_metrics_endpoint_returns_200():
    """Тест: /metrics возвращает 200 и правильный content-type."""
    app = web.Application()
    setup_metrics_routes(app)

    async with TestClient(TestServer(app)) as client:
        resp = await client.get("/metrics")
        assert resp.status == 200
        assert "text/plain" in resp.headers.get("Content-Type", "")
        body = await resp.text()
        assert "# HELP" in body or "# TYPE" in body or body == ""


async def test_metrics_endpoint_contains_registered_metrics():
    """Тест: /metrics содержит зарегистрированные метрики из REGISTRY."""
    from services.metrics.registry import payment_total

    payment_total.labels(status="test_http", operation="test_http").inc()

    app = web.Application()
    setup_metrics_routes(app)

    async with TestClient(TestServer(app)) as client:
        resp = await client.get("/metrics")
        body = await resp.text()
        assert "vpn_payment_total" in body
