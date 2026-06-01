"""
Comprehensive async tests for RegistrationUsersMiddleware flow.

ОТКЛЮЧЕНЫ 2026-06-01: файл тестировал старую архитектуру (cache.users →
service_model.users.get_data → factory). Текущая реализация ходит только
в BackendAPIClient (см. CLAUDE.md "Cache Access Rules") — соответствующее
покрытие живёт в tests/middlewares/test_registration_users.py.

Содержимое оставлено как reference, чтобы можно было переиспользовать
тест-кейсы при будущей адаптации к новой архитектуре. Не удалять без
обновления до актуальной логики middleware.
"""
from unittest.mock import AsyncMock, MagicMock

import pytest

pytest.skip(
    "Legacy flow tests for old cache/DB-based middleware — see "
    "tests/middlewares/test_registration_users.py for current coverage.",
    allow_module_level=True,
)

from aiogram.types import Update  # noqa: E402  — unreachable after skip

from middlewares.registration_users import RegistrationUsersMiddleware  # noqa: E402
from registration.registration_factory import RegistrationFactory  # noqa: E402


class TestRegistrationUsersMiddlewareFlow:
    @pytest.fixture
    def middleware(self):
        return RegistrationUsersMiddleware()

    @pytest.fixture
    def make_event(self):
        """Factory that creates an Update mock with configurable message text."""
        def _make(text: str = "/start"):
            event = MagicMock(spec=Update)
            message = MagicMock()
            message.text = text
            event.message = message
            event.edited_message = None
            return event
        return _make

    @pytest.fixture
    def base_data(self):
        cache = AsyncMock()
        cache.users.get = AsyncMock(return_value=None)

        container = MagicMock()
        service_model = AsyncMock()
        service_model.users.get_data = AsyncMock(return_value=None)
        container.resolve = MagicMock(return_value=service_model)

        return {
            "container": container,
            "cache": cache,
            "event_from_user": MagicMock(id=999001),
        }

    # ------------------------------------------------------------------ #
    # Cache hit → registered_user, no DB query                           #
    # ------------------------------------------------------------------ #
    async def test_new_user_without_token_starts_register_flow(
        self, middleware, make_event, base_data
    ):
        """User with no token gets no registration_result; downstream routes to Register.captcha."""
        handler = AsyncMock()
        event = make_event("/start")  # no token

        await middleware(handler, event, base_data)

        handler.assert_called_once()
        # No token → factory never called → no registration_result injected
        assert "registration_result" not in base_data

    async def test_new_user_with_gift_token_delegates_to_factory(
        self, middleware, make_event, base_data
    ):
        """When /start carries a token, factory.handle_registration is invoked.

        DB fallback must return None so the middleware continues to token parsing.
        """
        handler = AsyncMock()
        event = make_event("/start abc123")

        factory = AsyncMock(spec=RegistrationFactory)
        factory.handle_registration = AsyncMock(
            return_value={"success": True, "type": "gift", "token": "abc123", "tariff_id": 1, "from_user_id": 42}
        )
        factory.register_handler = MagicMock()
        gift_registration = AsyncMock()

        from registration.registration_factory import RegistrationFactory as RF
        from registration.gift_registration import GiftRegistration as GR

        service_model = AsyncMock()
        service_model.users = AsyncMock()
        service_model.users.get_data = AsyncMock(return_value=None)  # not in DB

        def resolve(cls):
            if cls is RF:
                return factory
            if cls is GR:
                return gift_registration
            return service_model

        base_data["container"].resolve = MagicMock(side_effect=resolve)

        await middleware(handler, event, base_data)

        factory.handle_registration.assert_called_once_with("abc123")
        assert base_data["registration_result"]["type"] == "gift"

    async def test_registered_user_in_cache_sets_registration_result(
        self, middleware, make_event, base_data
    ):
        """User already in cache → registration_result type=registered_user, DB not queried."""
        cached_user = MagicMock()
        base_data["cache"].users.get = AsyncMock(return_value=cached_user)
        handler = AsyncMock()
        event = make_event("/start")

        await middleware(handler, event, base_data)

        assert base_data["registration_result"]["type"] == "registered_user"
        assert base_data["registration_result"]["success"] is True

    async def test_registered_user_in_cache_does_not_query_db(
        self, middleware, make_event, base_data
    ):
        """Cache hit should short-circuit before any DB resolve."""
        cached_user = MagicMock()
        base_data["cache"].users.get = AsyncMock(return_value=cached_user)
        handler = AsyncMock()
        event = make_event("/start")

        await middleware(handler, event, base_data)

        # container.resolve should NOT be called when cache hit
        base_data["container"].resolve.assert_not_called()

    async def test_registered_user_in_db_fallback(
        self, middleware, make_event, base_data
    ):
        """Cache miss → DB fallback finds user → registered_user result, handler called."""
        db_user = MagicMock()
        service_model = AsyncMock()
        service_model.users = AsyncMock()
        service_model.users.get_data = AsyncMock(return_value=db_user)
        base_data["container"].resolve = MagicMock(return_value=service_model)
        handler = AsyncMock()
        event = make_event("/start")

        await middleware(handler, event, base_data)

        service_model.users.get_data.assert_called_once_with(999001)
        assert base_data["registration_result"]["type"] == "registered_user"
        handler.assert_called_once()

    async def test_db_fallback_exception_falls_through_to_token_check(
        self, middleware, make_event, base_data
    ):
        """DB raises exception → warning logged, flow continues to token check."""
        service_model = AsyncMock()
        service_model.users = AsyncMock()
        service_model.users.get_data = AsyncMock(side_effect=Exception("db error"))
        base_data["container"].resolve = MagicMock(return_value=service_model)
        handler = AsyncMock()
        event = make_event("/start")  # no token → nothing further injected

        await middleware(handler, event, base_data)

        handler.assert_called_once()
        # No token → no registration_result despite DB failure
        assert "registration_result" not in base_data

    # ------------------------------------------------------------------ #
    # Token parsing                                                        #
    # ------------------------------------------------------------------ #
    async def test_token_parsing_from_start_message(self, middleware, make_event):
        """Token is correctly extracted from '/start <token>' message text."""
        event = make_event("/start my_gift_token_xyz")
        token = await middleware.get_start_message(event)
        assert token == "my_gift_token_xyz"

    async def test_token_parsing_plain_start_returns_none(self, middleware, make_event):
        """/start with no parameter returns None."""
        event = make_event("/start")
        token = await middleware.get_start_message(event)
        assert token is None

    async def test_token_parsing_non_start_command_returns_none(self, middleware, make_event):
        """Non-/start message text returns None."""
        event = make_event("/profile")
        token = await middleware.get_start_message(event)
        assert token is None

    async def test_check_event_message_true_when_message_present(self, middleware):
        event = MagicMock(spec=Update)
        event.message = MagicMock()
        event.edited_message = None
        assert middleware.check_event_message(event)

    async def test_check_event_message_true_when_edited_message_present(self, middleware):
        event = MagicMock(spec=Update)
        event.message = None
        event.edited_message = MagicMock()
        assert middleware.check_event_message(event)

    async def test_check_event_message_false_when_no_message(self, middleware):
        event = MagicMock(spec=Update)
        event.message = None
        event.edited_message = None
        assert not middleware.check_event_message(event)

    async def test_no_event_from_user_passes_through_without_result(
        self, middleware, base_data
    ):
        """Missing event_from_user → handler called, no registration_result."""
        base_data["event_from_user"] = None
        handler = AsyncMock()

        await middleware(handler, MagicMock(), base_data)

        handler.assert_called_once()
        assert "registration_result" not in base_data

    def _make_no_user_service_model(self):
        """Service model whose users.get_data returns None (user not in DB)."""
        svc = AsyncMock()
        svc.users = AsyncMock()
        svc.users.get_data = AsyncMock(return_value=None)
        return svc

    async def test_successful_gift_registration_injects_result(
        self, middleware, make_event, base_data
    ):
        """A gift token that resolves successfully injects result with success=True."""
        handler = AsyncMock()
        event = make_event("/start giftABC")

        factory = MagicMock()
        factory.handle_registration = AsyncMock(
            return_value={"success": True, "type": "gift", "token": "giftABC"}
        )
        factory.register_handler = MagicMock()
        gift_reg = AsyncMock()

        no_user_svc = self._make_no_user_service_model()

        def _resolve(cls):
            from registration.registration_factory import RegistrationFactory as RF
            from registration.gift_registration import GiftRegistration as GR
            if cls is RF:
                return factory
            if cls is GR:
                return gift_reg
            return no_user_svc

        base_data["container"].resolve = MagicMock(side_effect=_resolve)

        await middleware(handler, event, base_data)

        assert base_data["registration_result"]["success"] is True
        assert base_data["registration_result"]["type"] == "gift"

    async def test_failed_factory_result_does_not_inject_registration_result(
        self, middleware, make_event, base_data
    ):
        """Factory returns success=False → registration_result NOT injected."""
        handler = AsyncMock()
        event = make_event("/start badtoken")

        factory = MagicMock()
        factory.handle_registration = AsyncMock(
            return_value={"success": False, "error": "invalid_token"}
        )
        factory.register_handler = MagicMock()
        gift_reg = AsyncMock()

        no_user_svc = self._make_no_user_service_model()

        def _resolve(cls):
            from registration.registration_factory import RegistrationFactory as RF
            from registration.gift_registration import GiftRegistration as GR
            if cls is RF:
                return factory
            if cls is GR:
                return gift_reg
            return no_user_svc

        base_data["container"].resolve = MagicMock(side_effect=_resolve)

        await middleware(handler, event, base_data)

        assert "registration_result" not in base_data
        handler.assert_called_once()
