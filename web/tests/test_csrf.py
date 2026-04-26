import pytest
from httpx import AsyncClient, ASGITransport
from app.main import app


@pytest.fixture(autouse=True)
def enable_csrf_for_this_module(monkeypatch):
    """Re-enable CSRF for these specific tests."""
    from app.core import config
    monkeypatch.setattr(config.settings, "csrf_enabled", True)


@pytest.mark.asyncio
async def test_csrf_blocks_post_without_token():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        resp = await c.post("/api/v1/keys/", json={})
    assert resp.status_code == 403
    assert "CSRF" in resp.json()["detail"]


@pytest.mark.asyncio
async def test_csrf_allows_post_with_matching_token():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        c.cookies.set("csrf_token", "test-csrf-value")
        resp = await c.post(
            "/api/v1/keys/",
            json={},
            headers={"X-CSRF-Token": "test-csrf-value"},
        )
    # Not 403 — may be 401 (no auth cookie) or 422 (validation)
    assert resp.status_code != 403


@pytest.mark.asyncio
async def test_csrf_allows_auth_endpoints_without_token():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        resp = await c.post("/api/v1/auth/login", json={"code": "TESTCODE1"})
    # Not 403
    assert resp.status_code != 403


@pytest.mark.asyncio
async def test_csrf_allows_bot_endpoint_without_token():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        resp = await c.post(
            "/api/v1/bot/auth/generate-code",
            json={"tg_id": 123},
            headers={"X-Bot-Secret": "test"},
        )
    assert resp.status_code != 403


@pytest.mark.asyncio
async def test_csrf_allows_get_requests():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        resp = await c.get("/api/v1/auth/me")
    assert resp.status_code != 403
