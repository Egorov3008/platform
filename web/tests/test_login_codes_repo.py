import pytest
from unittest.mock import AsyncMock, patch
from datetime import datetime, timezone
from app.repositories.login_codes import LoginCodesRepo


@pytest.mark.asyncio
async def test_create_returns_code_and_expires_at():
    repo = LoginCodesRepo()
    conn = AsyncMock()
    fake_expires = datetime(2026, 4, 20, 10, 0, 0, tzinfo=timezone.utc)
    conn.fetchrow = AsyncMock(return_value={"code": "ABCD1234", "expires_at": fake_expires})

    with patch("app.repositories.login_codes.generate_login_code", return_value="ABCD1234"):
        code, expires_at = await repo.create(conn, tg_id=123, ttl_hours=24)

    assert code == "ABCD1234"
    assert expires_at == fake_expires
    conn.fetchrow.assert_called_once()
    args = conn.fetchrow.call_args[0]
    assert "INSERT INTO login_codes" in args[0]
    assert args[1] == "ABCD1234"
    assert args[2] == 123


@pytest.mark.asyncio
async def test_consume_valid_code():
    repo = LoginCodesRepo()
    conn = AsyncMock()
    conn.fetchrow = AsyncMock(return_value={"id": 1, "code": "ABCD1234", "tg_id": 123, "used": True})

    result = await repo.consume(conn, "abcd1234")  # lowercase — should be uppercased

    assert result is not None
    assert result["tg_id"] == 123
    args = conn.fetchrow.call_args[0]
    assert "ABCD1234" in args  # uppercased


@pytest.mark.asyncio
async def test_consume_invalid_code_returns_none():
    repo = LoginCodesRepo()
    conn = AsyncMock()
    conn.fetchrow = AsyncMock(return_value=None)

    result = await repo.consume(conn, "BADCODE1")

    assert result is None
