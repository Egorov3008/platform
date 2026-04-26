"""
Тесты для паттернов _DB_FIELDS и _name (Этап 8).

Покрывает:
- to_dict() исключает id из моделей с _DB_FIELDS (PaymentModel, GiftLink, ReferralLink,
  ReferralRedemption, ReferralReward)
- to_dict() не включает ClassVar _name в результат (через asdict)
- from_dict() принимает id из SELECT (roundtrip через БД)
- _name ClassVar доступен как свойство и как атрибут класса
- Key._DB_FIELDS (исходный паттерн) работает корректно
- Tariff/Server (без _DB_FIELDS) включают id в to_dict — это нормально
- GiftLink._status (не ClassVar, а instance field с _ prefix) включается в asdict,
  но исключается _DB_FIELDS-фильтром в to_dict()
"""

from dataclasses import asdict
from datetime import datetime

from models.payments.payment import PaymentModel
from models.gifts.gift_link import GiftLink
from models.referrals.referral_link import ReferralLink
from models.referrals.referral_redemption import ReferralRedemption
from models.referrals.referral_reward import ReferralReward
from models.keys.key import Key
from models.tariffs.tariff import Tariff
from models.servers.server import Server
from models.stocks.stock import Stock


# ---------------------------------------------------------------------------
# _name ClassVar: не попадает в asdict, доступен через свойство .name
# ---------------------------------------------------------------------------


class TestNameClassVar:
    """_name = ClassVar[str] не сериализуется через asdict, но доступен через .name"""

    def test_payment_name_not_in_asdict(self):
        p = PaymentModel(payment_id="p1", tg_id=1, amount=100)
        assert "_name" not in asdict(p)

    def test_payment_name_property(self):
        p = PaymentModel(payment_id="p1", tg_id=1, amount=100)
        assert p.name == "payment"
        assert PaymentModel._name == "payment"

    def test_tariff_name_not_in_asdict(self):
        t = Tariff(id=1, name_tariff="Basic", amount=500)
        assert "_name" not in asdict(t)

    def test_tariff_name_property(self):
        t = Tariff(id=1, name_tariff="Basic", amount=500)
        assert t.name == "tariff"
        assert Tariff._name == "tariff"

    def test_server_name_not_in_asdict(self):
        s = Server(
            id=1,
            cluster_name="c",
            server_name="s",
            api_url="u",
            subscription_url="su",
            login="l",
            password="p",
        )
        assert "_name" not in asdict(s)

    def test_server_name_property(self):
        s = Server(
            id=1,
            cluster_name="c",
            server_name="s",
            api_url="u",
            subscription_url="su",
            login="l",
            password="p",
        )
        assert s.name == "servers"
        assert Server._name == "servers"

    def test_stock_name_not_in_asdict(self):
        stock = Stock(tg_id=1, stock_type="fix", value=10)
        assert "_name" not in asdict(stock)

    def test_stock_name_property(self):
        stock = Stock(tg_id=1, stock_type="fix", value=10)
        assert stock.name == "stock"
        assert Stock._name == "stock"

    def test_gift_link_name_not_in_asdict(self):
        # _name ClassVar не попадает в asdict;
        # _status — instance field, он попадает в asdict (это нормально)
        gift = GiftLink(sender_tg_id=1, tariff_id=1, token="tok")
        d = asdict(gift)
        assert "_name" not in d
        assert "_status" in d  # instance field с _ — asdict его включает

    def test_gift_link_name_property(self):
        gift = GiftLink(sender_tg_id=1, tariff_id=1, token="tok")
        assert gift.name == "gift_links"
        assert GiftLink._name == "gift_links"


# ---------------------------------------------------------------------------
# PaymentModel: _DB_FIELDS исключает id из INSERT, id доступен при чтении
# ---------------------------------------------------------------------------


class TestPaymentModelDBFields:
    def test_to_dict_excludes_id(self):
        p = PaymentModel(payment_id="p1", tg_id=1, amount=100, id=42)
        d = p.to_dict()
        assert "id" not in d

    def test_to_dict_contains_required_fields(self):
        p = PaymentModel(
            payment_id="p1", tg_id=1, amount=100, payment_type="card", status="success"
        )
        d = p.to_dict()
        assert set(d.keys()) == {
            "payment_id",
            "tg_id",
            "amount",
            "payment_type",
            "status",
            "number_of_months",
            "created_at",
        }

    def test_to_dict_excludes_name(self):
        # _name — ClassVar, asdict его не включает, фильтр _DB_FIELDS тоже
        p = PaymentModel(payment_id="p1", tg_id=1, amount=100)
        d = p.to_dict()
        assert "_name" not in d
        assert "name" not in d

    def test_from_dict_accepts_id_from_select(self):
        """SELECT возвращает id — from_dict должен принимать его без ошибки."""
        data = {
            "payment_id": "p_sel",
            "tg_id": 5,
            "amount": 999.0,
            "payment_type": "crypto",
            "status": "success",
            "created_at": datetime.now(),
            "id": 77,
        }
        p = PaymentModel.from_dict(data)
        assert p.id == 77
        assert p.payment_id == "p_sel"

    def test_from_dict_without_id(self):
        """from_dict без id — id=None по умолчанию."""
        data = {
            "payment_id": "p_new",
            "tg_id": 5,
            "amount": 100.0,
            "payment_type": "card",
            "status": "success",
            "created_at": datetime.now(),
        }
        p = PaymentModel.from_dict(data)
        assert p.id is None

    def test_to_dict_used_for_insert_has_no_id(self):
        """Симуляция INSERT: to_dict() → kwargs для BaseRepository.create()."""
        p = PaymentModel(payment_id="p_insert", tg_id=1, amount=50)
        insert_data = p.to_dict()
        # id не передаётся в INSERT — БД генерирует его сама (SERIAL)
        assert "id" not in insert_data
        # Все обязательные поля присутствуют
        assert "payment_id" in insert_data
        assert "created_at" in insert_data

    def test_db_fields_whitelist_matches_model(self):
        """_DB_FIELDS содержит ровно те поля, что нужны для INSERT."""
        expected = {
            "payment_id",
            "tg_id",
            "amount",
            "payment_type",
            "status",
            "number_of_months",
            "created_at",
        }
        assert PaymentModel._DB_FIELDS == frozenset(expected)


# ---------------------------------------------------------------------------
# GiftLink: _DB_FIELDS исключает id и _status
# ---------------------------------------------------------------------------


class TestGiftLinkDBFields:
    def test_to_dict_excludes_id(self):
        gift = GiftLink(sender_tg_id=1, tariff_id=1, token="tok", id=99)
        d = gift.to_dict()
        assert "id" not in d

    def test_to_dict_excludes_status(self):
        """_status — instance field, но _DB_FIELDS его не включает."""
        gift = GiftLink(sender_tg_id=1, tariff_id=1, token="tok")
        d = gift.to_dict()
        assert "_status" not in d
        # NOTE: "status" тоже не в _DB_FIELDS — поле в БД не хранится как "status"
        assert "status" not in d

    def test_to_dict_contains_required_fields(self):
        gift = GiftLink(sender_tg_id=1, tariff_id=1, token="tok")
        d = gift.to_dict()
        assert set(d.keys()) == {
            "sender_tg_id",
            "tariff_id",
            "token",
            "created_at",
            "recipient_tg_id",
            "email",
            "used_at",
        }

    def test_from_dict_accepts_id_from_select(self):
        """SELECT возвращает id — from_dict должен принимать его."""
        data = {
            "sender_tg_id": 1,
            "tariff_id": 2,
            "token": "tok_sel",
            "id": 55,
            "created_at": datetime.now(),
            "recipient_tg_id": None,
            "email": None,
            "used_at": None,
        }
        gift = GiftLink.from_dict(data)
        assert gift.id == 55
        assert gift.token == "tok_sel"

    def test_asdict_includes_status_as_instance_field(self):
        """asdict включает _status (это instance field, не ClassVar)."""
        gift = GiftLink(sender_tg_id=1, tariff_id=1, token="tok")
        d = asdict(gift)
        assert "_status" in d
        assert d["_status"] == "active"

    def test_db_fields_whitelist_correct(self):
        expected = {
            "sender_tg_id",
            "tariff_id",
            "token",
            "created_at",
            "recipient_tg_id",
            "email",
            "used_at",
        }
        assert GiftLink._DB_FIELDS == frozenset(expected)


# ---------------------------------------------------------------------------
# ReferralLink: _DB_FIELDS исключает id
# ---------------------------------------------------------------------------


class TestReferralLinkDBFields:
    def test_to_dict_excludes_id(self):
        rl = ReferralLink(referrer_tg_id=1, token="ref_tok", id=10)
        d = rl.to_dict()
        assert "id" not in d

    def test_to_dict_contains_required_fields(self):
        rl = ReferralLink(referrer_tg_id=1, token="ref_tok")
        d = rl.to_dict()
        assert set(d.keys()) == {"referrer_tg_id", "token", "created_at"}

    def test_from_dict_accepts_id_from_select(self):
        data = {
            "referrer_tg_id": 1,
            "token": "ref_tok",
            "created_at": datetime.now(),
            "id": 15,
        }
        rl = ReferralLink.from_dict(data)
        assert rl.id == 15
        assert rl.referrer_tg_id == 1

    def test_from_dict_without_id(self):
        data = {
            "referrer_tg_id": 1,
            "token": "ref_tok",
            "created_at": datetime.now(),
        }
        rl = ReferralLink.from_dict(data)
        assert rl.id is None

    def test_created_at_auto_set(self):
        """created_at устанавливается автоматически если None."""
        rl = ReferralLink(referrer_tg_id=1, token="tok")
        assert rl.created_at is not None
        assert isinstance(rl.created_at, datetime)

    def test_db_fields_whitelist_correct(self):
        assert ReferralLink._DB_FIELDS == frozenset(
            {"referrer_tg_id", "token", "created_at"}
        )


# ---------------------------------------------------------------------------
# ReferralRedemption: _DB_FIELDS исключает id
# ---------------------------------------------------------------------------


class TestReferralRedemptionDBFields:
    def test_to_dict_excludes_id(self):
        rr = ReferralRedemption(referral_link_id=1, referred_tg_id=99, id=7)
        d = rr.to_dict()
        assert "id" not in d

    def test_to_dict_contains_required_fields(self):
        rr = ReferralRedemption(referral_link_id=1, referred_tg_id=99)
        d = rr.to_dict()
        assert set(d.keys()) == {"referral_link_id", "referred_tg_id", "redeemed_at"}

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

    def test_redeemed_at_auto_set(self):
        rr = ReferralRedemption(referral_link_id=1, referred_tg_id=99)
        assert rr.redeemed_at is not None
        assert isinstance(rr.redeemed_at, datetime)

    def test_db_fields_whitelist_correct(self):
        assert ReferralRedemption._DB_FIELDS == frozenset(
            {"referral_link_id", "referred_tg_id", "redeemed_at"}
        )


# ---------------------------------------------------------------------------
# ReferralReward: _DB_FIELDS исключает id
# ---------------------------------------------------------------------------


class TestReferralRewardDBFields:
    def test_to_dict_excludes_id(self):
        rew = ReferralReward(
            referrer_tg_id=1, reward_type="percent", reward_value="10", id=20
        )
        d = rew.to_dict()
        assert "id" not in d

    def test_to_dict_contains_required_fields(self):
        rew = ReferralReward(referrer_tg_id=1, reward_type="percent", reward_value="10")
        d = rew.to_dict()
        assert set(d.keys()) == {
            "referrer_tg_id",
            "reward_type",
            "reward_value",
            "awarded_at",
            "is_claimed",
        }

    def test_from_dict_accepts_id_from_select(self):
        data = {
            "referrer_tg_id": 1,
            "reward_type": "percent",
            "reward_value": "10",
            "awarded_at": datetime.now(),
            "is_claimed": False,
            "id": 20,
        }
        rew = ReferralReward.from_dict(data)
        assert rew.id == 20
        assert rew.reward_type == "percent"

    def test_awarded_at_auto_set(self):
        rew = ReferralReward(referrer_tg_id=1, reward_type="percent", reward_value="10")
        assert rew.awarded_at is not None
        assert isinstance(rew.awarded_at, datetime)

    def test_is_claimed_default_false(self):
        rew = ReferralReward(referrer_tg_id=1, reward_type="fix", reward_value="50")
        assert rew.is_claimed is False

    def test_db_fields_whitelist_correct(self):
        assert ReferralReward._DB_FIELDS == frozenset(
            {
                "referrer_tg_id",
                "reward_type",
                "reward_value",
                "awarded_at",
                "is_claimed",
            }
        )


# ---------------------------------------------------------------------------
# Key: оригинальный паттерн _DB_FIELDS (не ClassVar) — регрессионный тест
# ---------------------------------------------------------------------------


class TestKeyDBFields:
    def test_to_dict_excludes_non_db_fields(self):
        """Key._DB_FIELDS исключает поля только для runtime: tariff_description, name_tariff и др."""
        key = Key(
            tg_id=1,
            client_id="c1",
            email="u@e.com",
            expiry_time=999,
            key="vkey",
            inbound_id=1,
            tariff_description="desc",
            name_tariff="Premium",
            amount=100.0,
        )
        d = key.to_dict()
        assert "tariff_description" not in d
        assert "name_tariff" not in d
        assert "amount" not in d
        assert "server_info" not in d

    def test_to_dict_contains_db_fields(self):
        key = Key(
            tg_id=1,
            client_id="c1",
            email="u@e.com",
            expiry_time=999,
            key="vkey",
            inbound_id=1,
        )
        d = key.to_dict()
        required = {
            "tg_id",
            "client_id",
            "email",
            "created_at",
            "expiry_time",
            "key",
            "total_gb",
            "reset_date",
            "inbound_id",
            "notified_10h",
            "notified_24h",
            "tariff_id",
        }
        assert set(d.keys()) == required

    def test_key_has_no_id_field(self):
        """Key не имеет поля id — нет SERIAL в таблице keys."""
        key = Key(
            tg_id=1,
            client_id="c1",
            email="u@e.com",
            expiry_time=999,
            key="vkey",
            inbound_id=1,
        )
        assert not hasattr(key, "id")


# ---------------------------------------------------------------------------
# Tariff и Server: нет _DB_FIELDS — to_dict() включает id (это нормально,
# id не SERIAL у этих таблиц — он задаётся вручную)
# ---------------------------------------------------------------------------


class TestTariffServerNoDBFields:
    def test_tariff_to_dict_includes_id(self):
        """Tariff не имеет _DB_FIELDS — id включается в to_dict (id не SERIAL)."""
        t = Tariff(id=1, name_tariff="Basic", amount=500)
        d = t.to_dict()
        assert "id" in d

    def test_server_to_dict_includes_id(self):
        """Server не имеет _DB_FIELDS — id включается в to_dict."""
        s = Server(
            id=1,
            cluster_name="c",
            server_name="s",
            api_url="u",
            subscription_url="su",
            login="l",
            password="p",
        )
        d = s.to_dict()
        assert "id" in d

    def test_tariff_from_dict_roundtrip(self):
        t = Tariff(id=5, name_tariff="Pro", amount=999, period=60, limit_ip=5)
        t2 = Tariff.from_dict(t.to_dict())
        assert t2.id == 5
        assert t2.name_tariff == "Pro"

    def test_server_from_dict_roundtrip(self):
        s = Server(
            id=2,
            cluster_name="EU",
            server_name="eu-1",
            api_url="https://eu.api",
            subscription_url="https://eu.sub",
            login="admin",
            password="secret",
        )
        s2 = Server.from_dict(s.to_dict())
        assert s2.id == 2
        assert s2.server_name == "eu-1"
