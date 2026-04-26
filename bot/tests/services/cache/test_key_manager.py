"""
Tests for CacheKeyManager - pure key generation logic.

CacheKeyManager is the single source of truth for all cache keys.
Every model has a specific identifier field that must be used:
- User → tg_id
- Key → email
- Server → id
- Tariff → id
- GiftLink → id
- Inbound → (server_id, inbound_id)
- PaymentModel → payment_id
- Stock → tg_id
"""

from services.cache.key_manager import CacheKeyManager


class TestCacheKeyManagerBasicKeys:
    """Test basic key generation for all entities"""

    def test_user_key(self):
        """CacheKeyManager.user() should generate user_{tg_id}"""
        assert CacheKeyManager.user(123) == "user_123"
        assert CacheKeyManager.user("456") == "user_456"
        assert CacheKeyManager.user(999999999) == "user_999999999"

    def test_key_key(self):
        """CacheKeyManager.key() should generate key_{email}"""
        assert CacheKeyManager.key("test@example.com") == "key_test@example.com"
        assert (
            CacheKeyManager.key("user+tag@domain.co.uk") == "key_user+tag@domain.co.uk"
        )

    def test_server_key(self):
        """CacheKeyManager.server() should generate server_{id}"""
        assert CacheKeyManager.server(1) == "server_1"
        assert CacheKeyManager.server(42) == "server_42"

    def test_tariff_key(self):
        """CacheKeyManager.tariff() should generate tariff_{id}"""
        assert CacheKeyManager.tariff(10) == "tariff_10"
        assert CacheKeyManager.tariff(5) == "tariff_5"

    def test_gift_key(self):
        """CacheKeyManager.gift() should generate gift_{id_or_token}"""
        assert CacheKeyManager.gift(1) == "gift_1"
        assert CacheKeyManager.gift("token_abc123") == "gift_token_abc123"

    def test_inbound_key(self):
        """CacheKeyManager.inbound() should generate inbound_{server_id}_{inbound_id}"""
        assert CacheKeyManager.inbound(1, 12) == "inbound_1_12"
        assert CacheKeyManager.inbound(2, 5) == "inbound_2_5"
        # Test with string IDs
        assert CacheKeyManager.inbound("1", "12") == "inbound_1_12"

    def test_payment_key(self):
        """CacheKeyManager.payment() should generate payment_{payment_id}"""
        assert CacheKeyManager.payment("yoo_12345") == "payment_yoo_12345"
        assert CacheKeyManager.payment("test_payment_123") == "payment_test_payment_123"

    def test_stock_key(self):
        """CacheKeyManager.stock() should generate stock_{tg_id}"""
        assert CacheKeyManager.stock(123) == "stock_123"
        assert CacheKeyManager.stock(999999999) == "stock_999999999"


class TestCacheKeyManagerSpecialKeys:
    """Test special key generation for registration and gift activation"""

    def test_registration_user_key(self):
        """CacheKeyManager.registration_user() for spam protection"""
        assert CacheKeyManager.registration_user(123) == "temporary_registration_user_123"
        assert CacheKeyManager.registration_user("456") == "temporary_registration_user_456"

    def test_gift_activation_key(self):
        """CacheKeyManager.gift_activation() for gift data during activation"""
        assert CacheKeyManager.gift_activation(123) == "from_gift_123"
        assert CacheKeyManager.gift_activation(999999999) == "from_gift_999999999"


class TestCacheKeyManagerTemporaryKeys:
    """Test temporary key generation with TTL"""

    def test_temporary_payment_data_key(self):
        """CacheKeyManager.temporary_payment_data() for 10-min TTL data"""
        assert CacheKeyManager.temporary_payment_data(123) == "temporary_payment_123"
        assert CacheKeyManager.temporary_payment_data("456") == "temporary_payment_456"

    def test_temporary_tariff_data_key(self):
        """CacheKeyManager.temporary_tariff_data() for pre-payment tariff data"""
        assert CacheKeyManager.temporary_tariff_data(123) == "temporary_tariff_123"

    def test_temporary_inbound_key(self):
        """CacheKeyManager.temporary_inbound() for inbound_id storage"""
        assert CacheKeyManager.temporary_inbound(123) == "temporary_inbound_123"


class TestCacheKeyManagerHelpers:
    """Test helper methods for key manipulation"""

    def test_extract_id_from_basic_key(self):
        """extract_id() should recover the ID from a key"""
        assert CacheKeyManager.extract_id("user_123") == "123"
        assert CacheKeyManager.extract_id("server_42") == "42"
        assert CacheKeyManager.extract_id("stock_999999999") == "999999999"

    def test_extract_id_from_email_key(self):
        """extract_id() should handle email (with underscore)"""
        # Key format: key_user@example.com
        assert CacheKeyManager.extract_id("key_test@example.com") == "test@example.com"

    def test_extract_id_from_inbound_key(self):
        """extract_id() should handle inbound key with multiple underscores"""
        # Format: inbound_1_12 → should return "1_12"
        assert CacheKeyManager.extract_id("inbound_1_12") == "1_12"
        assert CacheKeyManager.extract_id("inbound_2_5") == "2_5"

    def test_extract_id_from_payment_key(self):
        """extract_id() should handle payment_id with underscores"""
        assert (
            CacheKeyManager.extract_id("payment_test_payment_123") == "test_payment_123"
        )
        assert CacheKeyManager.extract_id("payment_yoo_12345") == "yoo_12345"

    def test_extract_id_invalid(self):
        """extract_id() should handle invalid keys gracefully"""
        assert CacheKeyManager.extract_id("invalid") is None
        assert CacheKeyManager.extract_id("") is None

    def test_is_temporary_true(self):
        """is_temporary() should return True for temporary keys"""
        assert CacheKeyManager.is_temporary("temporary_payment_123") is True
        assert CacheKeyManager.is_temporary("temporary_tariff_456") is True
        assert CacheKeyManager.is_temporary("temporary_inbound_789") is True
        assert CacheKeyManager.is_temporary("temporary_registration_user_456") is True

    def test_is_temporary_false(self):
        """is_temporary() should return False for non-temporary keys"""
        assert CacheKeyManager.is_temporary("user_123") is False
        assert CacheKeyManager.is_temporary("key_test@example.com") is False
        assert CacheKeyManager.is_temporary("payment_yoo_123") is False


class TestCacheKeyManagerConsistency:
    """Test consistency and determinism of key generation"""

    def test_key_generation_deterministic(self):
        """Same input should always produce same key"""
        key1 = CacheKeyManager.user(123)
        key2 = CacheKeyManager.user(123)
        assert key1 == key2

    def test_different_ids_different_keys(self):
        """Different IDs should produce different keys"""
        key1 = CacheKeyManager.user(123)
        key2 = CacheKeyManager.user(124)
        assert key1 != key2

    def test_inbound_key_order_matters(self):
        """Inbound key should use correct order (server_id, inbound_id)"""
        key1 = CacheKeyManager.inbound(1, 12)
        key2 = CacheKeyManager.inbound(12, 1)
        assert key1 != key2
        assert key1 == "inbound_1_12"
        assert key2 == "inbound_12_1"

    def test_all_keys_unique_prefixes(self):
        """Each entity type should have unique prefix"""
        test_cases = [
            (CacheKeyManager.user(1), "user_"),
            (CacheKeyManager.key("test@ex.com"), "key_"),
            (CacheKeyManager.server(1), "server_"),
            (CacheKeyManager.tariff(1), "tariff_"),
            (CacheKeyManager.gift(1), "gift_"),
            (CacheKeyManager.inbound(1, 1), "inbound_"),
            (CacheKeyManager.payment("test"), "payment_"),
            (CacheKeyManager.stock(1), "stock_"),
        ]

        for key, prefix in test_cases:
            assert key.startswith(prefix), f"Key {key} doesn't start with {prefix}"


class TestCacheKeyManagerEdgeCases:
    """Test edge cases and special inputs"""

    def test_zero_ids(self):
        """Should handle zero as ID"""
        assert CacheKeyManager.user(0) == "user_0"
        assert CacheKeyManager.server(0) == "server_0"

    def test_large_ids(self):
        """Should handle very large numbers"""
        large_id = 9999999999999999
        assert CacheKeyManager.user(large_id) == f"user_{large_id}"

    def test_special_characters_in_email(self):
        """Should handle special characters in email"""
        email = "user+tag@sub-domain.co.uk"
        key = CacheKeyManager.key(email)
        assert key == f"key_{email}"

    def test_payment_id_with_special_chars(self):
        """Should handle payment_id with special characters"""
        payment_id = "yoo_123abc_456def"
        key = CacheKeyManager.payment(payment_id)
        assert key == f"payment_{payment_id}"

    def test_string_and_int_equivalence(self):
        """Numeric IDs can be passed as int or str"""
        # Note: These produce different keys! This is important to document
        key_int = CacheKeyManager.user(123)
        key_str = CacheKeyManager.user("123")
        assert key_int == "user_123"
        assert key_str == "user_123"
        assert key_int == key_str
