import time

from models.payments.payment import PaymentModel


class TestPayment:
    def test_payment_creation(self):
        payment = PaymentModel(
            payment_id="pay_123",
            tg_id=123,
            amount=1000,
            payment_type="card",
            status="pending",
        )
        assert payment.payment_id == "pay_123"
        assert payment.tg_id == 123
        assert payment.amount == 1000
        assert payment.payment_type == "card"
        assert payment.status == "pending"
        assert payment.number_of_months == 1

    def test_payment_defaults(self):
        payment = PaymentModel(payment_id="pay_123", tg_id=123, amount=1000)
        assert payment.payment_type is None
        assert payment.status == "pending"
        assert payment.number_of_months == 1

    def test_payment_with_number_of_months(self):
        payment = PaymentModel(
            payment_id="pay_456",
            tg_id=456,
            amount=3000,
            payment_type="card",
            number_of_months=3,
        )
        assert payment.number_of_months == 3

    def test_payment_number_of_months_in_db_fields(self):
        assert "number_of_months" in PaymentModel._DB_FIELDS

    def test_payment_to_dict_includes_number_of_months(self):
        payment = PaymentModel(
            payment_id="pay_789",
            tg_id=789,
            amount=6000,
            payment_type="card",
            number_of_months=6,
        )
        d = payment.to_dict()
        assert d["number_of_months"] == 6

    def test_payment_from_dict_with_number_of_months(self):
        data = {
            "payment_id": "pay_abc",
            "tg_id": 111,
            "amount": 2000,
            "payment_type": "card",
            "status": "pending",
            "number_of_months": 2,
        }
        payment = PaymentModel.from_dict(data)
        assert payment.number_of_months == 2

    def test_created_at_unique_per_instance(self):
        """Два экземпляра получают разные created_at (не мутабельный дефолт)."""
        p1 = PaymentModel(payment_id="pay_1")
        time.sleep(0.01)
        p2 = PaymentModel(payment_id="pay_2")
        assert p1.created_at != p2.created_at

    def test_status_default_is_pending(self):
        """Статус по умолчанию — pending, не success."""
        payment = PaymentModel(payment_id="pay_test")
        assert payment.status == "pending"
