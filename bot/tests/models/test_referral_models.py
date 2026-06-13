"""
Тесты для моделей реферальной системы (Этап 8).

Покрывает ReferralLink, ReferralRedemption, ReferralReward:
- Создание с обязательными полями
- _DB_FIELDS корректно исключает id из to_dict()
- from_dict() принимает id из SELECT
- Автоматическая инициализация datetime-полей через __post_init__
- Optional type hints работают корректно (created_at, redeemed_at, awarded_at)
"""

from datetime import datetime
from decimal import Decimal

from models.referrals.referral_link import ReferralLink
from models.referrals.referral_redemption import ReferralRedemption
from models.referrals.referral_reward import ReferralReward


# ---------------------------------------------------------------------------
# ReferralLink
# ---------------------------------------------------------------------------


class TestReferralLink:
    def test_creation_minimal(self):
        rl = ReferralLink(referrer_tg_id=100, token="ref_abc")
        assert rl.referrer_tg_id == 100
        assert rl.token == "ref_abc"
        assert rl.id is None

    def test_created_at_auto_set(self):
        """__post_init__ устанавливает created_at если None."""
        rl = ReferralLink(referrer_tg_id=100, token="ref_abc")
        assert rl.created_at is not None
        assert isinstance(rl.created_at, datetime)

    def test_created_at_explicit(self):
        """Явно переданный created_at сохраняется."""
        dt = datetime(2025, 1, 15, 12, 0, 0)
        rl = ReferralLink(referrer_tg_id=100, token="ref_abc", created_at=dt)
        assert rl.created_at == dt

    def test_to_dict_excludes_id(self):
        rl = ReferralLink(referrer_tg_id=100, token="ref_abc", id=42)
        d = rl.to_dict()
        assert "id" not in d

    def test_to_dict_contains_correct_fields(self):
        rl = ReferralLink(referrer_tg_id=100, token="ref_abc")
        d = rl.to_dict()
        assert set(d.keys()) == {"referrer_tg_id", "token", "created_at"}
        assert d["referrer_tg_id"] == 100
        assert d["token"] == "ref_abc"

    def test_from_dict_accepts_id_from_select(self):
        """SELECT возвращает id — from_dict() обязан его принять."""
        data = {
            "referrer_tg_id": 100,
            "token": "ref_abc",
            "created_at": datetime.now(),
            "id": 7,
        }
        rl = ReferralLink.from_dict(data)
        assert rl.id == 7
        assert rl.referrer_tg_id == 100

    def test_from_dict_without_id(self):
        """from_dict() без id — id остаётся None."""
        data = {
            "referrer_tg_id": 100,
            "token": "ref_abc",
            "created_at": datetime.now(),
        }
        rl = ReferralLink.from_dict(data)
        assert rl.id is None

    def test_to_dict_then_from_dict_roundtrip(self):
        """to_dict() → from_dict() сохраняет данные (без id)."""
        rl = ReferralLink(referrer_tg_id=200, token="roundtrip")
        rl2 = ReferralLink.from_dict(rl.to_dict())
        assert rl2.referrer_tg_id == 200
        assert rl2.token == "roundtrip"
        assert rl2.id is None  # id не было в to_dict

    def test_db_fields_whitelist(self):
        assert ReferralLink._DB_FIELDS == frozenset(
            {"referrer_tg_id", "token", "created_at"}
        )


# ---------------------------------------------------------------------------
# ReferralRedemption
# ---------------------------------------------------------------------------


class TestReferralRedemption:
    def test_creation_minimal(self):
        rr = ReferralRedemption(referral_link_id=1, referred_tg_id=99)
        assert rr.referral_link_id == 1
        assert rr.referred_tg_id == 99
        assert rr.id is None

    def test_redeemed_at_auto_set(self):
        rr = ReferralRedemption(referral_link_id=1, referred_tg_id=99)
        assert rr.redeemed_at is not None
        assert isinstance(rr.redeemed_at, datetime)

    def test_redeemed_at_explicit(self):
        dt = datetime(2025, 3, 10, 8, 0, 0)
        rr = ReferralRedemption(referral_link_id=1, referred_tg_id=99, redeemed_at=dt)
        assert rr.redeemed_at == dt

    def test_to_dict_excludes_id(self):
        rr = ReferralRedemption(referral_link_id=1, referred_tg_id=99, id=5)
        d = rr.to_dict()
        assert "id" not in d

    def test_to_dict_contains_correct_fields(self):
        rr = ReferralRedemption(referral_link_id=1, referred_tg_id=99)
        d = rr.to_dict()
        assert set(d.keys()) == {"referral_link_id", "referred_tg_id", "redeemed_at"}
        assert d["referral_link_id"] == 1
        assert d["referred_tg_id"] == 99

    def test_from_dict_accepts_id_from_select(self):
        data = {
            "referral_link_id": 1,
            "referred_tg_id": 99,
            "redeemed_at": datetime.now(),
            "id": 3,
        }
        rr = ReferralRedemption.from_dict(data)
        assert rr.id == 3
        assert rr.referred_tg_id == 99

    def test_from_dict_without_id(self):
        data = {
            "referral_link_id": 1,
            "referred_tg_id": 99,
            "redeemed_at": datetime.now(),
        }
        rr = ReferralRedemption.from_dict(data)
        assert rr.id is None

    def test_db_fields_whitelist(self):
        assert ReferralRedemption._DB_FIELDS == frozenset(
            {"referral_link_id", "referred_tg_id", "redeemed_at"}
        )


# ---------------------------------------------------------------------------
# ReferralReward
# ---------------------------------------------------------------------------


class TestReferralReward:
    def test_creation_minimal(self):
        rew = ReferralReward(referrer_tg_id=1, reward_type="percent", reward_value="10")
        assert rew.referrer_tg_id == 1
        assert rew.reward_type == "percent"
        # BUG-8: reward_value хранится как Decimal (TEXT→DECIMAL(10,2) в БД),
        # __post_init__ нормализует str → Decimal.
        assert rew.reward_value == Decimal("10")
        assert isinstance(rew.reward_value, Decimal)
        assert rew.id is None

    def test_awarded_at_auto_set(self):
        rew = ReferralReward(referrer_tg_id=1, reward_type="fix", reward_value="50")
        assert rew.awarded_at is not None
        assert isinstance(rew.awarded_at, datetime)

    def test_awarded_at_explicit(self):
        dt = datetime(2025, 6, 1, 0, 0, 0)
        rew = ReferralReward(
            referrer_tg_id=1, reward_type="fix", reward_value="50", awarded_at=dt
        )
        assert rew.awarded_at == dt

    def test_to_dict_excludes_id(self):
        rew = ReferralReward(
            referrer_tg_id=1, reward_type="percent", reward_value="10", id=20
        )
        d = rew.to_dict()
        assert "id" not in d

    def test_to_dict_contains_correct_fields(self):
        rew = ReferralReward(referrer_tg_id=1, reward_type="percent", reward_value="10")
        d = rew.to_dict()
        assert set(d.keys()) == {
            "referrer_tg_id",
            "reward_type",
            "reward_value",
            "awarded_at",
        }
        assert d["reward_type"] == "percent"

    def test_from_dict_accepts_id_from_select(self):
        data = {
            "referrer_tg_id": 1,
            "reward_type": "percent",
            "reward_value": "10",
            "awarded_at": datetime.now(),
            "id": 20,
        }
        rew = ReferralReward.from_dict(data)
        assert rew.id == 20
        assert rew.reward_type == "percent"

    def test_from_dict_without_id(self):
        data = {
            "referrer_tg_id": 1,
            "reward_type": "fix",
            "reward_value": "100",
            "awarded_at": datetime.now(),
        }
        rew = ReferralReward.from_dict(data)
        assert rew.id is None

    def test_db_fields_whitelist(self):
        assert ReferralReward._DB_FIELDS == frozenset(
            {
                "referrer_tg_id",
                "reward_type",
                "reward_value",
                "awarded_at",
            }
        )

    def test_to_dict_then_from_dict_roundtrip(self):
        rew = ReferralReward(
            referrer_tg_id=42, reward_type="percent", reward_value="15"
        )
        rew2 = ReferralReward.from_dict(rew.to_dict())
        assert rew2.referrer_tg_id == 42
        # BUG-8: reward_value остаётся Decimal после roundtrip
        assert rew2.reward_value == Decimal("15")
        assert isinstance(rew2.reward_value, Decimal)
        assert rew2.id is None  # id не был в to_dict
