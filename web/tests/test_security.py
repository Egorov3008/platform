"""Модульные тесты функций безопасности.

Проверяют корректность bcrypt-хеширования паролей, создание/декодирование
JWT-токенов и поведение при истёкшем сроке действия.
"""

import pytest
from datetime import timedelta
from app.core.security import (
    hash_password, verify_password,
    create_access_token, create_refresh_token,
    decode_token, create_token,
)


def test_password_hash_and_verify():
    hashed = hash_password("mysecret")
    assert verify_password("mysecret", hashed) is True
    assert verify_password("wrong", hashed) is False


def test_create_and_decode_access_token():
    payload = {"sub": "42", "tg_id": 123, "is_admin": False}
    token = create_access_token(payload)
    decoded = decode_token(token)
    assert decoded["sub"] == "42"
    assert decoded["tg_id"] == 123
    assert decoded["is_admin"] is False


def test_expired_token_raises():
    token = create_token({"sub": "1"}, expires_delta=timedelta(seconds=-1))
    with pytest.raises(ValueError):
        decode_token(token)
