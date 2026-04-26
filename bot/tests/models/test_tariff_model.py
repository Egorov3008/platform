from models.tariffs.tariff import Tariff


class TestTariff:
    def test_tariff_creation(self):
        tariff = Tariff(
            id=1,
            name_tariff="Premium",
            amount=1000,
            description="Premium plan",
            limit_ip=5,
            period=30,
            traffic_limit=100,
        )
        assert tariff.id == 1
        assert tariff.name_tariff == "Premium"
        assert tariff.amount == 1000
        assert tariff.description == "Premium plan"
        assert tariff.limit_ip == 5
        assert tariff.period == 30
        assert tariff.traffic_limit == 100

    def test_tariff_defaults(self):
        tariff = Tariff(id=1, name_tariff="Basic", amount=500)
        assert tariff.period == 30
        assert tariff.traffic_limit == 0.0
