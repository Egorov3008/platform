import hashlib
import hmac as hmac_lib
import random
import time


class CaptchaError(ValueError):
    pass


def generate_captcha(secret: str) -> dict:
    """Генерирует арифметическую капчу со stateless HMAC-токеном.

    Возвращает словарь с question (например "5 + 7"), token (HMAC-подпись)
    и timestamp. Ответ НЕ передаётся клиенту — он восстанавливается на
    сервере при проверке через проверку HMAC-подписи.
    """
    a = random.randint(1, 15)
    b = random.randint(1, 15)
    answer = a + b
    timestamp = int(time.time())
    token = hmac_lib.new(
        secret.encode(),
        f"{answer}:{timestamp}".encode(),
        hashlib.sha256,
    ).hexdigest()
    return {"question": f"{a} + {b}", "token": token, "timestamp": timestamp}


def verify_captcha(answer: int, timestamp: int, token: str, secret: str) -> None:
    """Проверяет ответ на капчу через HMAC.

    Капча валидна 5 минут (300 секунд). Использует hmac.compare_digest
    для защиты от timing-атак. Бросает CaptchaError при истечении срока
    или неверном ответе.
    """
    if int(time.time()) - timestamp > 300:
        raise CaptchaError("Captcha expired")
    expected = hmac_lib.new(
        secret.encode(),
        f"{answer}:{timestamp}".encode(),
        hashlib.sha256,
    ).hexdigest()
    if not hmac_lib.compare_digest(expected, token):
        raise CaptchaError("Wrong captcha answer")
