"""
Тесты для модели GiftLink.

Исправления относительно предыдущей версии (Этап 8):
1. to_dict() НЕ включает ключ "status" — _status исключён через _DB_FIELDS.
   Убраны ассерты `data["status"] == "active"`.
2. from_dict() НЕ принимает ключ "status" — это не поле dataclass.
   Тест переписан: from_dict принимает поля dataclass (в т.ч. id из SELECT).
3. Добавлены тесты для _DB_FIELDS и roundtrip через to_dict/from_dict.
"""

import pytest
from datetime import datetime, timedelta

from models.gifts.gift_link import GiftLink


def test_gift_link_creation():
    """Тест создания объекта GiftLink."""
    gift = GiftLink(sender_tg_id=123, tariff_id=7, token="test_token")

    assert gift.sender_tg_id == 123
    assert gift.tariff_id == 7
    assert gift.token == "test_token"
    assert gift._status == "active"
    assert gift.created_at is not None
    assert gift.recipient_tg_id is None
    assert gift.used_at is None


def test_gift_link_to_dict():
    """to_dict() возвращает только _DB_FIELDS: без id и без _status."""
    gift = GiftLink(sender_tg_id=123, tariff_id=7, token="test_token")
    data = gift.to_dict()

    assert data["sender_tg_id"] == 123
    assert data["tariff_id"] == 7
    assert data["token"] == "test_token"

    # id исключён (_DB_FIELDS не содержит id)
    assert "id" not in data
    # _status исключён (_DB_FIELDS не содержит _status / status)
    assert "_status" not in data
    assert "status" not in data

    # Присутствуют все ожидаемые поля
    assert set(data.keys()) == {
        "sender_tg_id",
        "tariff_id",
        "token",
        "created_at",
        "recipient_tg_id",
        "email",
        "used_at",
    }


def test_gift_link_from_dict_minimal():
    """from_dict создаёт объект из минимального набора полей."""
    data = {
        "sender_tg_id": 123,
        "tariff_id": 7,
        "token": "test_token",
        "created_at": datetime.now(),
        "recipient_tg_id": None,
        "email": None,
        "used_at": None,
    }
    gift = GiftLink.from_dict(data)

    assert gift.sender_tg_id == data["sender_tg_id"]
    assert gift.tariff_id == data["tariff_id"]
    assert gift.token == data["token"]
    # _status вычисляется через __post_init__, не из данных
    assert gift._status == "active"


def test_gift_link_from_dict_with_id_from_select():
    """from_dict принимает id, возвращаемый SELECT запросом."""
    data = {
        "sender_tg_id": 123,
        "tariff_id": 7,
        "token": "test_token",
        "id": 55,
        "created_at": datetime.now(),
        "recipient_tg_id": None,
        "email": None,
        "used_at": None,
    }
    gift = GiftLink.from_dict(data)
    assert gift.id == 55
    assert gift.sender_tg_id == 123


def test_gift_link_from_dict_with_status_key_fails():
    """
    from_dict НЕ принимает ключ 'status' — это не поле dataclass.
    Тест документирует это поведение: если код передаёт 'status',
    будет TypeError. Использовать следует '_status' или не передавать совсем.
    """
    data = {
        "sender_tg_id": 123,
        "tariff_id": 7,
        "token": "test_token",
        "status": "active",  # неверный ключ
    }
    with pytest.raises(TypeError):
        GiftLink.from_dict(data)


def test_gift_link_redeem_success():
    """Тест успешной активации подарка."""
    gift = GiftLink(sender_tg_id=123, tariff_id=7, token="test_token")
    recipient_id = 456
    email = "test@example.com"

    gift.redeem(recipient_id, email)

    assert gift.recipient_tg_id == recipient_id
    assert gift.email == email
    assert gift.used_at is not None
    assert gift._status == "redeemed"


def test_gift_link_redeem_self():
    """Тест попытки активации подарка самому себе."""
    gift = GiftLink(sender_tg_id=123, tariff_id=7, token="test_token")

    with pytest.raises(ValueError, match="Нельзя активировать подарок самому себе"):
        gift.redeem(123, "test@example.com")


def test_gift_link_redeem_inactive():
    """Тест попытки активации уже активированного подарка."""
    gift = GiftLink(sender_tg_id=123, tariff_id=7, token="test_token")
    gift.redeem(456, "test@example.com")

    with pytest.raises(ValueError, match="Подарок недоступен для активации"):
        gift.redeem(789, "other@example.com")


def test_gift_link_is_redeemable():
    """Тест проверки доступности подарка для активации."""
    active_gift = GiftLink(sender_tg_id=123, tariff_id=7, token="test_token")
    assert active_gift.is_redeemable() is True

    active_gift.redeem(456, "test@example.com")
    assert active_gift.is_redeemable() is False


def test_gift_link_is_expired():
    """Тест проверки истечения срока действия подарка."""
    past_date = datetime.now() - timedelta(days=1)
    gift = GiftLink(
        sender_tg_id=123, tariff_id=7, token="test_token", created_at=past_date
    )
    assert gift.is_expired(max_days=30) is False

    past_date = datetime.now() - timedelta(days=31)
    gift = GiftLink(
        sender_tg_id=123, tariff_id=7, token="test_token", created_at=past_date
    )
    assert gift.is_expired(max_days=30) is True

    past_date = datetime.now() - timedelta(days=30)
    gift = GiftLink(
        sender_tg_id=123, tariff_id=7, token="test_token", created_at=past_date
    )
    assert gift.is_expired(max_days=30) is False


def test_gift_link_status_property():
    """Статус доступен через свойство .status."""
    gift = GiftLink(sender_tg_id=123, tariff_id=7, token="test_token")
    assert gift.status == "active"

    gift.redeem(456, "t@e.com")
    assert gift.status == "redeemed"
