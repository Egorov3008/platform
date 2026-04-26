import pytest
from app.core.security import generate_login_code


def test_generate_login_code_length():
    code = generate_login_code()
    assert len(code) == 8


def test_generate_login_code_charset():
    code = generate_login_code()
    assert code.isalnum()
    assert code == code.upper()


def test_generate_login_code_unique():
    codes = {generate_login_code() for _ in range(100)}
    assert len(codes) == 100
