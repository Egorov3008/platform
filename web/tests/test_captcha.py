import time
import pytest
from app.core.captcha import generate_captcha, verify_captcha, CaptchaError

SECRET = "test_captcha_secret"


def test_generate_captcha_structure():
    result = generate_captcha(SECRET)
    assert "question" in result
    assert "token" in result
    assert "timestamp" in result
    assert "+" in result["question"]


def test_verify_correct_answer():
    cap = generate_captcha(SECRET)
    question = cap["question"]
    # parse "a + b" from question string
    parts = question.split("+")
    answer = int(parts[0].strip()) + int(parts[1].strip())
    verify_captcha(answer, cap["timestamp"], cap["token"], SECRET)  # should not raise


def test_verify_wrong_answer():
    cap = generate_captcha(SECRET)
    with pytest.raises(CaptchaError, match="Wrong"):
        verify_captcha(99999, cap["timestamp"], cap["token"], SECRET)


def test_verify_expired():
    cap = generate_captcha(SECRET)
    old_ts = int(time.time()) - 400  # 6+ minutes ago
    with pytest.raises(CaptchaError, match="expired"):
        verify_captcha(0, old_ts, cap["token"], SECRET)
