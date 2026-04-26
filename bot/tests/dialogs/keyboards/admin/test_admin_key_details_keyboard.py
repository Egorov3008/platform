"""
Tests for AdminKeyDetailsKeyboard async handlers.

Handlers tested:
- _to_delete()        — deletes key from cache via CacheKeyManager
- _on_renew_key()     — adds 30 days (in ms) to expiry_time, resets notification flags, saves to cache and DB
- _to_change_tariff() — opens tariff change dialog

All handlers access cache via manager.middleware_data["cache"].
CacheService.keys.delete() and CacheService.keys.set() are mocked.
"""

from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, PropertyMock

from models import Key
from dialogs.windows.widgets.keybord.admin.keys_list import AdminKeyDetailsKeyboard
from services.core.keys.utils.reset import KeyResetter

MS_PER_DAY = 24 * 3600 * 1000


def make_key(email: str = "test@vpn.com", tg_id: int = 111, notified_24h: bool = True, notified_10h: bool = True) -> Key:
    now_ms = int(datetime.now(timezone.utc).timestamp() * 1000)
    return Key(
        email=email,
        tg_id=tg_id,
        client_id="c1",
        key="k",
        inbound_id=1,
        expiry_time=now_ms + 10 * MS_PER_DAY,
        tariff_id=1,
        notified_24h=notified_24h,
        notified_10h=notified_10h,
    )


def make_callback():
    """Build a minimal CallbackQuery mock."""
    cb = AsyncMock()
    cb.answer = AsyncMock()
    return cb


def make_manager(selected_key=None, cache=None, container=None):
    """Build a DialogManager mock with dialog_data and middleware_data."""
    manager = AsyncMock()
    manager.dialog_data = {}
    manager.middleware_data = {}
    if selected_key is not None:
        manager.dialog_data["selected_key"] = selected_key
    if cache is not None:
        manager.middleware_data["cache"] = cache
    if container is not None:
        manager.middleware_data["container"] = container
    return manager


def make_cache():
    """Build a CacheService mock with async keys.delete() and keys.set()."""
    cache = AsyncMock()
    cache.keys = AsyncMock()
    cache.keys.delete = AsyncMock()
    cache.keys.set = AsyncMock()
    return cache


def make_container():
    """Build a container mock with resolve() method."""
    container = AsyncMock()
    container.resolve = MagicMock()
    
    # Setup mocks for dependencies
    mock_pool = AsyncMock()
    mock_pool.execute = AsyncMock(return_value="UPDATE 1")
    
    mock_model_data = MagicMock()
    mock_model_data.keys = MagicMock()
    mock_model_data.keys.update = AsyncMock()
    
    # Mock KeyResetter that actually resets flags on the key object
    mock_resetter = AsyncMock()
    
    async def reset_key_after_renewal_side_effect(pool, key):
        """Side effect that resets flags on the key object."""
        key.notified_24h = False
        key.notified_10h = False
        key.used_traffic = 0.0
        return True
    
    mock_resetter.reset_key_after_renewal = AsyncMock(side_effect=reset_key_after_renewal_side_effect)
    
    def resolve_side_effect(item):
        if "asyncpg.Pool" in str(item) or item == "asyncpg.Pool":
            return mock_pool
        elif "ServiceDataModel" in str(item) or item == "ServiceDataModel":
            return mock_model_data
        elif "KeyResetter" in str(item) or item == KeyResetter:
            return mock_resetter
        return None
    
    container.resolve.side_effect = resolve_side_effect
    return container


# ---------------------------------------------------------------------------
# _to_delete()
# ---------------------------------------------------------------------------


class TestOnDeleteKey:
    async def test_opens_delete_dialog_with_email(self):
        """_to_delete() must open delete dialog with key's email."""
        key = make_key("delete_me@vpn.com")
        cache = make_cache()
        manager = make_manager(selected_key=key, cache=cache)
        callback = make_callback()
        manager.start = AsyncMock()

        await AdminKeyDetailsKeyboard._to_delete(callback, None, manager)

        manager.start.assert_called_once()
        call_args = manager.start.call_args
        assert call_args[0][0] is not None  # Dialog start point
        assert call_args[1]["data"]["email"] == "delete_me@vpn.com"

    async def test_no_selected_key_does_not_open_dialog(self):
        """When dialog_data has no selected_key, start() should not be called."""
        manager = make_manager(selected_key=None, cache=make_cache())
        callback = make_callback()
        manager.start = AsyncMock()

        await AdminKeyDetailsKeyboard._to_delete(callback, None, manager)

        manager.start.assert_not_called()

    async def test_no_cache_still_opens_dialog(self):
        """When cache is absent, dialog should still open (cache not used)."""
        key = make_key()
        manager = make_manager(selected_key=key, cache=None)
        callback = make_callback()
        manager.start = AsyncMock()

        await AdminKeyDetailsKeyboard._to_delete(callback, None, manager)

        manager.start.assert_called_once()


# ---------------------------------------------------------------------------
# _on_renew_key()
# ---------------------------------------------------------------------------


class TestOnRenewKey:
    async def test_renew_adds_30_days_in_ms(self):
        """_on_renew_key() must add exactly 30 days (in ms) to expiry_time."""
        key = make_key("renew@vpn.com")
        original_expiry = key.expiry_time
        cache = make_cache()
        container = make_container()
        manager = make_manager(selected_key=key, cache=cache, container=container)
        callback = make_callback()

        await AdminKeyDetailsKeyboard._on_renew_key(callback, None, manager)

        expected_expiry = original_expiry + 30 * MS_PER_DAY
        assert key.expiry_time == expected_expiry

    async def test_renew_resets_notification_flags(self):
        """_on_renew_key() must reset notified_24h and notified_10h to False via KeyResetter."""
        key = make_key("renew@vpn.com", notified_24h=True, notified_10h=True)
        cache = make_cache()
        container = make_container()
        manager = make_manager(selected_key=key, cache=cache, container=container)
        callback = make_callback()

        await AdminKeyDetailsKeyboard._on_renew_key(callback, None, manager)

        # KeyResetter.reset_key_after_renewal() должен быть вызван и сбросить флаги
        assert key.notified_24h is False
        assert key.notified_10h is False
        assert key.used_traffic == 0.0

    async def test_renewed_key_saved_to_cache(self):
        """After renewal, cache.keys.set() must be called with the updated key."""
        key = make_key("save@vpn.com")
        cache = make_cache()
        container = make_container()
        manager = make_manager(selected_key=key, cache=cache, container=container)
        callback = make_callback()

        await AdminKeyDetailsKeyboard._on_renew_key(callback, None, manager)

        cache.keys.set.assert_called_once()

    async def test_renewed_key_saved_to_db(self):
        """After renewal, model_data.keys.update() must be called."""
        key = make_key("db_save@vpn.com")
        cache = make_cache()
        container = make_container()
        manager = make_manager(selected_key=key, cache=cache, container=container)
        callback = make_callback()

        # Setup container to return mock pool and model_data
        mock_pool = AsyncMock()
        mock_model_data = MagicMock()
        mock_model_data.keys = MagicMock()
        mock_model_data.keys.update = AsyncMock()

        def resolve_side_effect(item):
            if "asyncpg.Pool" in str(item) or item == "asyncpg.Pool":
                return mock_pool
            elif "ServiceDataModel" in str(item) or item == "ServiceDataModel":
                return mock_model_data
            return None

        container.resolve.side_effect = resolve_side_effect

        await AdminKeyDetailsKeyboard._on_renew_key(callback, None, manager)

        mock_model_data.keys.update.assert_called_once()

    async def test_success_answer_contains_email(self):
        """Success alert must mention the key's email."""
        key = make_key("renewed@vpn.com")
        cache = make_cache()
        container = make_container()
        manager = make_manager(selected_key=key, cache=cache, container=container)
        callback = make_callback()

        await AdminKeyDetailsKeyboard._on_renew_key(callback, None, manager)

        callback.answer.assert_called_once()
        args, kwargs = callback.answer.call_args
        answer_text = args[0] if args else kwargs.get("text", "")
        assert "renewed@vpn.com" in answer_text
        assert "✅" in answer_text

    async def test_no_selected_key_sends_error(self):
        """When no selected_key, _on_renew_key must send error alert."""
        manager = make_manager(selected_key=None, cache=make_cache())
        callback = make_callback()

        await AdminKeyDetailsKeyboard._on_renew_key(callback, None, manager)

        callback.answer.assert_called_once()
        args, kwargs = callback.answer.call_args
        answer_text = args[0] if args else kwargs.get("text", "")
        assert "❌" in answer_text

    async def test_no_cache_sends_error(self):
        """When cache is absent, _on_renew_key must send error alert."""
        key = make_key()
        manager = make_manager(selected_key=key, cache=None)
        callback = make_callback()

        await AdminKeyDetailsKeyboard._on_renew_key(callback, None, manager)

        callback.answer.assert_called_once()
        args, kwargs = callback.answer.call_args
        answer_text = args[0] if args else kwargs.get("text", "")
        assert "❌" in answer_text

    async def test_renewal_does_not_modify_email(self):
        """Renewal must not change the key's email attribute."""
        key = make_key("immutable@vpn.com")
        cache = make_cache()
        container = make_container()
        manager = make_manager(selected_key=key, cache=cache, container=container)
        callback = make_callback()

        await AdminKeyDetailsKeyboard._on_renew_key(callback, None, manager)

        assert key.email == "immutable@vpn.com"

    async def test_db_update_error_is_logged_but_not_raised(self):
        """DB update error should be logged but not interrupt renewal."""
        key = make_key("error_test@vpn.com")
        cache = make_cache()
        container = make_container()
        manager = make_manager(selected_key=key, cache=cache, container=container)
        callback = make_callback()

        mock_pool = AsyncMock()
        mock_model_data = MagicMock()
        mock_model_data.keys = MagicMock()
        mock_model_data.keys.update = AsyncMock(side_effect=Exception("DB error"))

        def resolve_side_effect(item):
            if "asyncpg.Pool" in str(item) or item == "asyncpg.Pool":
                return mock_pool
            elif "ServiceDataModel" in str(item) or item == "ServiceDataModel":
                return mock_model_data
            return None

        container.resolve.side_effect = resolve_side_effect

        # Should not raise
        await AdminKeyDetailsKeyboard._on_renew_key(callback, None, manager)

        # Cache should still be updated
        cache.keys.set.assert_called_once()
        # Success message should still be sent
        callback.answer.assert_called_once()


# ---------------------------------------------------------------------------
# _to_change_tariff()
# ---------------------------------------------------------------------------


class TestOnChangeTariff:
    async def test_opens_change_tariff_dialog(self):
        """_to_change_tariff() must open tariff change dialog when selected_key exists."""
        key = make_key("tariff@vpn.com")
        manager = make_manager(selected_key=key, cache=make_cache())
        callback = make_callback()
        manager.start = AsyncMock()

        await AdminKeyDetailsKeyboard._to_change_tariff(callback, None, manager)

        manager.start.assert_called_once()

    async def test_no_selected_key_sends_error(self):
        """When no selected_key, _to_change_tariff does nothing (no dialog opened)."""
        manager = make_manager(selected_key=None, cache=make_cache())
        callback = make_callback()
        manager.start = AsyncMock()

        await AdminKeyDetailsKeyboard._to_change_tariff(callback, None, manager)

        manager.start.assert_not_called()
