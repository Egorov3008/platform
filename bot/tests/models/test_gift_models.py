from models.gifts.gift_link import GiftLink


class TestGiftLink:
    def test_gift_link_creation(self):
        link = GiftLink(sender_tg_id=123, tariff_id=1, token="gift123")
        assert link.sender_tg_id == 123
        assert link.tariff_id == 1
        assert link.token == "gift123"

    def test_gift_link_defaults(self):
        link = GiftLink(sender_tg_id=123, tariff_id=1, token="gift123")
        assert link.created_at is not None
        assert link.id is None
