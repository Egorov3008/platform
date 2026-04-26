"""
Tests for GiftUrlGenerator service - pure URL generation logic.

GiftUrlGenerator.generate() creates a Telegram bot deep link for gift activation.
Pure logic: no I/O, no async, simple string formatting.
"""

from unittest.mock import patch


from services.core.gift.repositories.gen_url import GiftUrlGenerator


class TestGiftUrlGeneratorBasic:
    """Test basic GiftUrlGenerator.generate() functionality"""

    def test_generate_with_default_bot_name(self):
        """generate() should use BOT_NAME from config by default"""
        # The default is loaded from config at import time
        generator = GiftUrlGenerator()
        url = generator.generate("token123")

        # Should have valid format regardless of actual BOT_NAME
        assert url.startswith("https://t.me/")
        assert "?start=token123" in url

    def test_generate_with_custom_bot_name(self):
        """generate() should accept bot_name parameter"""
        generator = GiftUrlGenerator()
        url = generator.generate("token123", bot_name="my_custom_bot")

        assert url == "https://t.me/my_custom_bot?start=token123"

    def test_generate_url_format(self):
        """generate() should create valid Telegram bot deep link"""
        generator = GiftUrlGenerator()
        url = generator.generate("abc123xyz", bot_name="testbot")

        # Should have correct structure
        assert url.startswith("https://t.me/")
        assert "?start=" in url
        assert url.endswith("abc123xyz")


class TestGiftUrlGeneratorTokens:
    """Test generate() with various token formats"""

    def test_generate_with_short_token(self):
        """generate() should handle short tokens"""
        generator = GiftUrlGenerator()
        url = generator.generate("a", bot_name="bot")

        assert url == "https://t.me/bot?start=a"

    def test_generate_with_long_token(self):
        """generate() should handle long tokens"""
        long_token = "a" * 100
        generator = GiftUrlGenerator()
        url = generator.generate(long_token, bot_name="bot")

        assert long_token in url
        assert url == f"https://t.me/bot?start={long_token}"

    def test_generate_with_alphanumeric_token(self):
        """generate() should handle alphanumeric tokens"""
        generator = GiftUrlGenerator()
        token = "gift_token_abc123xyz789"
        url = generator.generate(token, bot_name="bot")

        assert token in url

    def test_generate_with_underscore_token(self):
        """generate() should handle tokens with underscores"""
        generator = GiftUrlGenerator()
        token = "gift_token_2024"
        url = generator.generate(token, bot_name="bot")

        assert url == f"https://t.me/bot?start={token}"

    def test_generate_with_dash_token(self):
        """generate() should handle tokens with dashes"""
        generator = GiftUrlGenerator()
        token = "gift-token-2024"
        url = generator.generate(token, bot_name="bot")

        assert url == f"https://t.me/bot?start={token}"


class TestGiftUrlGeneratorBotNames:
    """Test generate() with various bot names"""

    def test_generate_with_simple_bot_name(self):
        """generate() with simple bot name"""
        generator = GiftUrlGenerator()
        url = generator.generate("token", bot_name="mybot")

        assert url == "https://t.me/mybot?start=token"

    def test_generate_with_bot_name_underscore(self):
        """generate() with bot name containing underscore"""
        generator = GiftUrlGenerator()
        url = generator.generate("token", bot_name="my_awesome_bot")

        assert url == "https://t.me/my_awesome_bot?start=token"

    def test_generate_with_numeric_bot_name(self):
        """generate() with numeric bot name"""
        generator = GiftUrlGenerator()
        url = generator.generate("token", bot_name="bot123")

        assert url == "https://t.me/bot123?start=token"

    def test_generate_with_official_telegram_bot(self):
        """generate() with realistic bot name"""
        generator = GiftUrlGenerator()
        url = generator.generate("gift_abc123", bot_name="VPN_3xui_Bot")

        assert url == "https://t.me/VPN_3xui_Bot?start=gift_abc123"


class TestGiftUrlGeneratorDeterminism:
    """Test that GiftUrlGenerator is deterministic"""

    def test_generate_same_input_same_output(self):
        """Same token and bot_name should always produce same URL"""
        generator = GiftUrlGenerator()
        url1 = generator.generate("token123", "mybot")
        url2 = generator.generate("token123", "mybot")

        assert url1 == url2

    def test_generate_different_tokens_different_urls(self):
        """Different tokens should produce different URLs"""
        generator = GiftUrlGenerator()
        url1 = generator.generate("token1", "bot")
        url2 = generator.generate("token2", "bot")

        assert url1 != url2

    def test_generate_different_bots_different_urls(self):
        """Different bot names should produce different URLs"""
        generator = GiftUrlGenerator()
        url1 = generator.generate("token", "bot1")
        url2 = generator.generate("token", "bot2")

        assert url1 != url2

    def test_generate_multiple_instances_same_result(self):
        """Different GiftUrlGenerator instances should produce same result"""
        gen1 = GiftUrlGenerator()
        gen2 = GiftUrlGenerator()

        url1 = gen1.generate("token", "bot")
        url2 = gen2.generate("token", "bot")

        assert url1 == url2


class TestGiftUrlGeneratorImmutability:
    """Test that GiftUrlGenerator doesn't mutate state"""

    def test_generate_no_side_effects(self):
        """generate() should not have side effects"""
        generator = GiftUrlGenerator()

        # Generate multiple URLs
        generator.generate("token1", "bot1")
        generator.generate("token2", "bot2")
        generator.generate("token1", "bot1")

        # Result should be consistent
        url = generator.generate("token1", "bot1")
        assert url == "https://t.me/bot1?start=token1"

    def test_generate_preserves_token(self):
        """Token should appear unchanged in URL"""
        generator = GiftUrlGenerator()
        token = "unique_token_xyz"
        url = generator.generate(token)

        # Token should be in URL exactly as provided
        assert f"?start={token}" in url


class TestGiftUrlGeneratorConfigIntegration:
    """Test integration with BOT_NAME config"""

    def test_generate_uses_config_bot_name(self):
        """generate() without bot_name param should use config"""
        generator = GiftUrlGenerator()
        url = generator.generate("token")

        # Should use whatever BOT_NAME is in config
        assert url.startswith("https://t.me/")
        assert "?start=token" in url
        # Verify format is correct
        assert url.count("?start=") == 1

    def test_generate_param_overrides_config(self):
        """bot_name parameter should override config"""
        with patch("services.core.gift.repositories.gen_url.BOT_NAME", "config_bot"):
            generator = GiftUrlGenerator()
            url = generator.generate("token", bot_name="param_bot")

            # Parameter should take precedence
            assert url == "https://t.me/param_bot?start=token"
            assert "config_bot" not in url


class TestGiftUrlGeneratorEdgeCases:
    """Test edge cases"""

    def test_generate_empty_token(self):
        """generate() with empty token (edge case)"""
        generator = GiftUrlGenerator()
        url = generator.generate("", bot_name="bot")

        assert url == "https://t.me/bot?start="

    def test_generate_whitespace_in_token(self):
        """generate() with whitespace in token (unusual but possible)"""
        generator = GiftUrlGenerator()
        token = "token with spaces"
        url = generator.generate(token, bot_name="bot")

        # URL will contain spaces (might need encoding in real usage)
        assert token in url

    def test_generate_special_chars_in_token(self):
        """generate() with special characters (URL encoding not handled)"""
        generator = GiftUrlGenerator()
        token = "gift_2024-01-15_v2.0"
        url = generator.generate(token, bot_name="bot")

        assert token in url
