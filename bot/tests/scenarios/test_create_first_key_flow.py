"""
Comprehensive async tests for CreateFerstKeyScenario — full first-key creation flow.

Covers: get_data() with/without dialog_manager, can_handle() based on user.trial,
start() with trial/gift/no-key/exception paths, dialog state transitions.

Scenario API (post-refactor):
    CreateFerstKeyScenario(backend_client, dialog_manager=None)
    - get_data()  → Optional[dict] (raw user dict from backend)
    - can_handle() → bool (True if user is registered and trial == 0)
    - start(tg_id, server_id) → drives the full flow via backend_client
"""
from unittest.mock import AsyncMock

import pytest
from aiogram_dialog import StartMode

from api.schemas import KeyDTO
from services.scenarios.create_first_key_scenario import CreateFerstKeyScenario
from states.key import KeysInit


# ------------------------------------------------------------------ #
# Helpers                                                              #
# ------------------------------------------------------------------ #

def _make_user_dict(tg_id: int = 555001, trial: int = 0, server_id: int = 2) -> dict:
    """User dict returned by BackendAPIClient.get_user()."""
    return {"tg_id": tg_id, "trial": trial, "server_id": server_id}


def _make_key_dto(
    email: str = "trial@555001.vpn",
    tg_id: int = 555001,
    public_link: str = "vpn://trial_key",
    link_to_connect: str = "https://sub.example.com/trial_key",
) -> KeyDTO:
    return KeyDTO(
        email=email,
        tg_id=tg_id,
        inbound_id=11,
        client_id="abc123",
        key=public_link,
        expiry_time=9999999999000,
        tariff_id=1,
        name_tariff="Trial",
        used_traffic=0.0,
        public_link=public_link,
        link_to_connect=link_to_connect,
    )


def _make_dialog_manager(
    user_id: int = 555001,
    dialog_data: dict | None = None,
) -> AsyncMock:
    manager = AsyncMock()
    manager.event = AsyncMock()
    manager.event.from_user = AsyncMock()
    manager.event.from_user.id = user_id
    manager.dialog_data = dialog_data if dialog_data is not None else {}
    return manager


def _make_scenario(
    user: dict | None = None,
    key_dto: KeyDTO | None = None,
    dialog_manager: AsyncMock | None = None,
    create_trial_key_side_effect=None,
) -> tuple[CreateFerstKeyScenario, AsyncMock]:
    """Build a CreateFerstKeyScenario with mocked BackendAPIClient.

    Returns (scenario, backend_client_mock) for assertion convenience.
    """
    _user = user if user is not None else _make_user_dict()
    _key = key_dto if key_dto is not None else _make_key_dto(tg_id=_user["tg_id"])
    _dm = dialog_manager if dialog_manager is not None else _make_dialog_manager(_user["tg_id"])

    backend = AsyncMock()
    backend.get_user = AsyncMock(return_value=_user)
    if create_trial_key_side_effect is not None:
        backend.create_trial_key = AsyncMock(side_effect=create_trial_key_side_effect)
    else:
        backend.create_trial_key = AsyncMock(return_value=_key)

    scenario = CreateFerstKeyScenario(
        backend_client=backend,
        dialog_manager=_dm,
    )
    return scenario, backend


# ------------------------------------------------------------------ #
# Tests: get_data()                                                    #
# ------------------------------------------------------------------ #

class TestGetData:
    async def test_get_data_returns_user_dict(self):
        """get_data() returns whatever backend.get_user() returns."""
        user = _make_user_dict(trial=0)
        scenario, backend = _make_scenario(user=user)

        result = await scenario.get_data()

        assert result == user
        backend.get_user.assert_called_once_with(user["tg_id"])

    async def test_get_data_returns_none_for_unregistered(self):
        """Backend returns None → get_data() returns None."""
        backend = AsyncMock()
        backend.get_user = AsyncMock(return_value=None)
        scenario = CreateFerstKeyScenario(
            backend_client=backend,
            dialog_manager=_make_dialog_manager(),
        )

        result = await scenario.get_data()

        assert result is None

    async def test_get_data_no_dialog_manager_returns_none(self):
        """Without dialog_manager, get_data() short-circuits and returns None."""
        backend = AsyncMock()
        backend.get_user = AsyncMock()
        scenario = CreateFerstKeyScenario(
            backend_client=backend, dialog_manager=None
        )

        result = await scenario.get_data()

        assert result is None
        backend.get_user.assert_not_called()


# ------------------------------------------------------------------ #
# Tests: can_handle()                                                  #
# ------------------------------------------------------------------ #

class TestCanHandle:
    async def test_can_handle_true_when_trial_is_zero(self):
        """trial=0 → user has not used the trial period → scenario applies."""
        user = _make_user_dict(trial=0)
        scenario, _ = _make_scenario(user=user)

        result = await scenario.can_handle()

        assert result is True

    async def test_can_handle_false_when_trial_used(self):
        """trial=1 → already consumed trial → can_handle is False."""
        user = _make_user_dict(trial=1)
        scenario, _ = _make_scenario(user=user)

        result = await scenario.can_handle()

        assert result is False

    async def test_can_handle_false_when_user_unregistered(self):
        """Backend returns None (user not registered) → False, register first."""
        backend = AsyncMock()
        backend.get_user = AsyncMock(return_value=None)
        scenario = CreateFerstKeyScenario(
            backend_client=backend,
            dialog_manager=_make_dialog_manager(),
        )

        result = await scenario.can_handle()

        assert result is False

    async def test_can_handle_false_without_dialog_manager(self):
        """Without DialogManager, scenario cannot proceed → False."""
        backend = AsyncMock()
        backend.get_user = AsyncMock()
        scenario = CreateFerstKeyScenario(
            backend_client=backend, dialog_manager=None
        )

        result = await scenario.can_handle()

        assert result is False
        backend.get_user.assert_not_called()


# ------------------------------------------------------------------ #
# Tests: start() — happy paths                                         #
# ------------------------------------------------------------------ #

class TestStartTrialFlow:
    async def test_start_calls_backend_create_trial_key(self):
        """start() invokes backend.create_trial_key with tg_id."""
        user = _make_user_dict(tg_id=555002, trial=0)
        key = _make_key_dto(tg_id=555002)
        scenario, backend = _make_scenario(user=user, key_dto=key)

        await scenario.start(tg_id=555002, server_id=2)

        backend.create_trial_key.assert_awaited_once_with(555002, gift_token=None)

    async def test_start_passes_gift_token_from_dialog_data(self):
        """If dialog_data has 'gift_token', it is forwarded to backend."""
        user = _make_user_dict(tg_id=555003, trial=0)
        key = _make_key_dto(tg_id=555003)
        dm = _make_dialog_manager(user_id=555003, dialog_data={"gift_token": "gift_abc"})
        scenario, backend = _make_scenario(user=user, key_dto=key, dialog_manager=dm)

        await scenario.start(tg_id=555003, server_id=2)

        backend.create_trial_key.assert_awaited_once_with(555003, gift_token="gift_abc")

    async def test_start_registers_user_before_creating_key(self):
        """Unregistered user → backend.admin_register_user is called first."""
        user = _make_user_dict(tg_id=555004, trial=0)
        key = _make_key_dto(tg_id=555004)
        dm = _make_dialog_manager(user_id=555004)
        backend = AsyncMock()
        # First get_user returns None (unregistered), then after registration returns user
        backend.get_user = AsyncMock(side_effect=[None, user])
        backend.admin_register_user = AsyncMock(return_value=user)
        backend.create_trial_key = AsyncMock(return_value=key)
        scenario = CreateFerstKeyScenario(
            backend_client=backend, dialog_manager=dm
        )

        await scenario.start(tg_id=555004, server_id=2)

        backend.admin_register_user.assert_awaited_once()
        register_arg = backend.admin_register_user.await_args[0][0]
        assert register_arg["tg_id"] == 555004
        assert register_arg["server_id"] == 2
        assert register_arg["username"] == dm.event.from_user.username
        backend.create_trial_key.assert_awaited_once()

    async def test_start_with_gift_starts_gift_dialog(self):
        """Gift token present → dialog is KeysInit.create_gift_key."""
        user = _make_user_dict(tg_id=555010, trial=0)
        key = _make_key_dto(tg_id=555010)
        dm = _make_dialog_manager(user_id=555010, dialog_data={"gift_token": "gift_xyz"})
        scenario, _ = _make_scenario(user=user, key_dto=key, dialog_manager=dm)

        await scenario.start(tg_id=555010, server_id=2)

        dm.start.assert_called()
        started_state = dm.start.call_args[0][0]
        assert started_state == KeysInit.create_gift_key

    async def test_start_without_gift_starts_trial_dialog(self):
        """No gift token → dialog is KeysInit.create_trial."""
        user = _make_user_dict(tg_id=555011, trial=0)
        key = _make_key_dto(tg_id=555011)
        dm = _make_dialog_manager(user_id=555011)
        scenario, _ = _make_scenario(user=user, key_dto=key, dialog_manager=dm)

        await scenario.start(tg_id=555011, server_id=2)

        dm.start.assert_called()
        started_state = dm.start.call_args[0][0]
        assert started_state == KeysInit.create_trial

    async def test_start_passes_link_data_to_dialog(self):
        """Dialog receives public_link and link_to_connect in data dict."""
        user = _make_user_dict(tg_id=555012, trial=0)
        key = _make_key_dto(
            tg_id=555012,
            public_link="vpn://specific",
            link_to_connect="https://sub.example.com/specific",
        )
        dm = _make_dialog_manager(user_id=555012)
        scenario, _ = _make_scenario(user=user, key_dto=key, dialog_manager=dm)

        await scenario.start(tg_id=555012, server_id=2)

        call = dm.start.call_args
        data_arg = call[1].get("data") or (call[0][1] if len(call[0]) > 1 else None)
        assert data_arg is not None
        assert data_arg["public_link"] == "vpn://specific"
        assert data_arg["link_to_connect"] == "https://sub.example.com/specific"

    async def test_start_falls_back_to_key_field_when_dto_links_missing(self):
        """If public_link / link_to_connect are None, fallback to key field."""
        user = _make_user_dict(tg_id=555013, trial=0)
        key = _make_key_dto(
            tg_id=555013,
            public_link="vpn://fallback_key",
            link_to_connect="vpn://fallback_key",
        )
        # Simulate backend returning no separate link fields, only `key`
        key.public_link = None
        key.link_to_connect = None
        key.key = "vpn://fallback_key"
        dm = _make_dialog_manager(user_id=555013)
        scenario, _ = _make_scenario(user=user, key_dto=key, dialog_manager=dm)

        await scenario.start(tg_id=555013, server_id=2)

        call = dm.start.call_args
        data_arg = call[1].get("data") or (call[0][1] if len(call[0]) > 1 else None)
        assert data_arg["public_link"] == "vpn://fallback_key"
        assert data_arg["link_to_connect"] == "vpn://fallback_key"


# ------------------------------------------------------------------ #
# Tests: start() — error and edge paths                                #
# ------------------------------------------------------------------ #

class TestStartErrorHandling:
    async def test_start_routes_to_error_when_trial_already_used(self):
        """User with trial=1 → start() goes to KeysInit.error, no key creation."""
        user = _make_user_dict(tg_id=555020, trial=1)
        dm = _make_dialog_manager(user_id=555020)
        scenario, backend = _make_scenario(user=user, dialog_manager=dm)

        await scenario.start(tg_id=555020, server_id=2)

        backend.create_trial_key.assert_not_called()
        dm.start.assert_called()
        started_state = dm.start.call_args[0][0]
        assert started_state == KeysInit.error

    async def test_start_error_dialog_uses_reset_stack(self):
        """Error dialog is started with StartMode.RESET_STACK."""
        user = _make_user_dict(tg_id=555021, trial=1)
        dm = _make_dialog_manager(user_id=555021)
        scenario, _ = _make_scenario(user=user, dialog_manager=dm)

        await scenario.start(tg_id=555021, server_id=2)

        call_kwargs = dm.start.call_args[1]
        assert call_kwargs.get("mode") == StartMode.RESET_STACK

    async def test_start_routes_to_error_when_backend_returns_none(self):
        """create_trial_key returns None (failure) → KeysInit.error."""
        user = _make_user_dict(tg_id=555022, trial=0)
        dm = _make_dialog_manager(user_id=555022)
        backend = AsyncMock()
        backend.get_user = AsyncMock(return_value=user)
        backend.create_trial_key = AsyncMock(return_value=None)
        scenario = CreateFerstKeyScenario(
            backend_client=backend, dialog_manager=dm
        )

        await scenario.start(tg_id=555022, server_id=2)

        dm.start.assert_called()
        started_state = dm.start.call_args[0][0]
        assert started_state == KeysInit.error

    async def test_start_routes_to_error_when_user_registration_fails(self):
        """Unregistered + admin_register_user returns falsy → error dialog."""
        dm = _make_dialog_manager(user_id=555023)
        backend = AsyncMock()
        backend.get_user = AsyncMock(return_value=None)
        backend.admin_register_user = AsyncMock(return_value=None)
        backend.create_trial_key = AsyncMock()
        scenario = CreateFerstKeyScenario(
            backend_client=backend, dialog_manager=dm
        )

        await scenario.start(tg_id=555023, server_id=2)

        backend.create_trial_key.assert_not_called()
        dm.start.assert_called()
        started_state = dm.start.call_args[0][0]
        assert started_state == KeysInit.error

    async def test_start_routes_to_error_on_registration_no_dialog_manager(self):
        """Cannot register without DialogManager (no from_user data) → error."""
        backend = AsyncMock()
        backend.get_user = AsyncMock(return_value=None)
        backend.admin_register_user = AsyncMock()
        backend.create_trial_key = AsyncMock()
        scenario = CreateFerstKeyScenario(
            backend_client=backend, dialog_manager=None
        )

        # No exception: just early-return
        await scenario.start(tg_id=555024, server_id=2)

        backend.admin_register_user.assert_not_called()
        backend.create_trial_key.assert_not_called()

    async def test_start_routes_to_error_on_exception(self):
        """Unexpected exception from backend → caught, error dialog started."""
        user = _make_user_dict(tg_id=555025, trial=0)
        dm = _make_dialog_manager(user_id=555025)
        backend = AsyncMock()
        backend.get_user = AsyncMock(return_value=user)

        async def _explode(*args, **kwargs):
            raise RuntimeError("backend on fire")

        backend.create_trial_key = AsyncMock(side_effect=_explode)
        scenario = CreateFerstKeyScenario(
            backend_client=backend, dialog_manager=dm
        )

        await scenario.start(tg_id=555025, server_id=2)

        dm.start.assert_called()
        started_state = dm.start.call_args[0][0]
        assert started_state == KeysInit.error

    async def test_start_handles_no_dialog_manager_gracefully(self):
        """start() without dialog_manager must not raise even on errors."""
        user = _make_user_dict(tg_id=555026, trial=0)
        key = _make_key_dto(tg_id=555026)
        backend = AsyncMock()
        backend.get_user = AsyncMock(return_value=user)
        backend.create_trial_key = AsyncMock(return_value=key)
        scenario = CreateFerstKeyScenario(
            backend_client=backend, dialog_manager=None
        )

        # Should not raise
        await scenario.start(tg_id=555026, server_id=2)

        backend.create_trial_key.assert_awaited_once()
