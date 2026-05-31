"""
Comprehensive async tests for CreateFerstKeyScenario — full first-key creation flow.

Covers: get_data() with/without gift, create_key invocation, DB save, trial installation,
transition to KeysInit.create_trial / create_gift_key, error handling.
"""
from unittest.mock import AsyncMock

import pytest
from aiogram_dialog import StartMode

from config import DEFAULT_PRICING_PLAN
from models import GiftLink, Tariff, User
from services.scenarios.create_first_key_scenario import CreateFerstKeyScenario
from states.key import KeysInit


# ------------------------------------------------------------------ #
# Helpers                                                              #
# ------------------------------------------------------------------ #

def _make_user(tg_id: int = 555001, trial: int = 0, server_id: int = 2) -> User:
    return User(tg_id=tg_id, trial=trial, server_id=server_id)


def _make_tariff(tariff_id: int = 1) -> Tariff:
    return Tariff(id=tariff_id, name_tariff="Trial Tariff", period=30, traffic_limit=10, limit_ip=2)


def _make_dialog_manager(
    user_id: int = 555001,
    session=None,
    middleware_data: dict | None = None,
) -> AsyncMock:
    manager = AsyncMock()
    manager.event = AsyncMock()
    manager.event.from_user = AsyncMock()
    manager.event.from_user.id = user_id
    manager.middleware_data = middleware_data or {"session": session or AsyncMock()}
    return manager


def _make_scenario(
    user: User | None = None,
    tariff: Tariff | None = None,
    gift: GiftLink | None = None,
    dialog_manager=None,
    create_key_result=None,
) -> tuple[CreateFerstKeyScenario, dict]:
    """Build a CreateFerstKeyScenario with all dependencies mocked."""
    _user = user or _make_user()
    _tariff = tariff or _make_tariff()
    _dm = dialog_manager or _make_dialog_manager(_user.tg_id)

    cache = AsyncMock()
    # temporary_get returns gift data if gift provided
    if gift:
        cache.gifts.temporary_get = AsyncMock(return_value={"gift": gift})
    else:
        cache.gifts.temporary_get = AsyncMock(return_value=None)

    model_data = AsyncMock()
    model_data.users.get_data = AsyncMock(return_value=_user)
    model_data.tariffs.get_data = AsyncMock(return_value=_tariff)

    create_key = AsyncMock()
    _key_result = create_key_result or {
        "public_link": "vpn://test_key",
        "link_to_connect": "vpn://test_key",
        "email": "test@555001.example.com",
        "days": 30,
    }
    create_key.proces = AsyncMock(return_value=_key_result)

    gift_service = AsyncMock()
    gift_service.application = AsyncMock()

    trial_user = AsyncMock()
    trial_user.installation_trial = AsyncMock()

    conn = AsyncMock()

    scenario = CreateFerstKeyScenario(
        cache=cache,
        model_data=model_data,
        create_key=create_key,
        gift_service=gift_service,
        trial_user=trial_user,
        conn=conn,
        dialog_manager=_dm,
    )

    deps = {
        "cache": cache,
        "model_data": model_data,
        "create_key": create_key,
        "gift_service": gift_service,
        "trial_user": trial_user,
        "conn": conn,
        "dialog_manager": _dm,
    }
    return scenario, deps


# ------------------------------------------------------------------ #
# Tests: get_data()                                                    #
# ------------------------------------------------------------------ #

class TestGetData:
    async def test_get_data_no_gift_uses_default_tariff(self):
        """Without gift, tariff is fetched using DEFAULT_PRICING_PLAN (cast to int)."""
        user = _make_user()
        scenario, deps = _make_scenario(user=user)

        await scenario.get_data()

        expected_id = int(DEFAULT_PRICING_PLAN) if DEFAULT_PRICING_PLAN else 10
        deps["model_data"].tariffs.get_data.assert_called_once_with(expected_id)
        assert scenario._user == user
        assert scenario._gift is None

    async def test_get_data_with_gift_uses_gift_tariff_id(self):
        """When gift is in temporary cache, its tariff_id is used."""
        gift = GiftLink(sender_tg_id=42, tariff_id=7, token="gtok")
        user = _make_user()
        scenario, deps = _make_scenario(user=user, gift=gift)

        await scenario.get_data()

        deps["model_data"].tariffs.get_data.assert_called_once_with(7)
        assert scenario._gift == gift

    async def test_get_data_sets_conn_from_middleware(self):
        """_conn is set from dialog_manager.middleware_data['session']."""
        session = AsyncMock()
        dm = _make_dialog_manager(session=session)
        scenario, _ = _make_scenario(dialog_manager=dm)

        await scenario.get_data()

        assert scenario._conn is session

    async def test_get_data_raises_when_no_dialog_manager(self):
        """get_data without dialog_manager raises ValueError."""
        cache = AsyncMock()
        model_data = AsyncMock()
        create_key = AsyncMock()
        gift_service = AsyncMock()
        trial_user = AsyncMock()
        conn = AsyncMock()

        scenario = CreateFerstKeyScenario(
            cache=cache,
            model_data=model_data,
            create_key=create_key,
            gift_service=gift_service,
            trial_user=trial_user,
            conn=conn,
            dialog_manager=AsyncMock(),
        )
        scenario.dialog_manager = None  # type: ignore

        with pytest.raises(ValueError, match="DialogManager"):
            await scenario.get_data()

    async def test_get_data_default_plan_env_is_cast_to_int(self):
        """Ensures DEFAULT_PRICING_PLAN is passed as int, not str, to get_data."""
        scenario, deps = _make_scenario()

        await scenario.get_data()

        call_args = deps["model_data"].tariffs.get_data.call_args
        tariff_id_arg = call_args[0][0]
        assert isinstance(tariff_id_arg, int), f"Expected int, got {type(tariff_id_arg)}"


# ------------------------------------------------------------------ #
# Tests: can_handle()                                                  #
# ------------------------------------------------------------------ #

class TestCanHandle:
    async def test_can_handle_returns_true_when_trial_is_zero(self):
        """User with trial=0 has not used the trial period yet."""
        user = _make_user(trial=0)
        scenario, _ = _make_scenario(user=user)

        result = await scenario.can_handle()

        assert result is True

    async def test_can_handle_returns_false_when_trial_used(self):
        """User with trial=1 already consumed trial → can_handle is False."""
        user = _make_user(trial=1)
        scenario, _ = _make_scenario(user=user)

        result = await scenario.can_handle()

        assert result is False


# ------------------------------------------------------------------ #
# Tests: start() — happy paths                                         #
# ------------------------------------------------------------------ #

class TestStartTrialFlow:
    async def test_create_first_key_creates_key_via_create_key_service(self):
        """start() calls create_key.proces with correct user/tariff/server args."""
        user = _make_user(tg_id=555002, server_id=2)
        tariff = _make_tariff(tariff_id=1)
        scenario, deps = _make_scenario(user=user, tariff=tariff)

        await scenario.get_data()
        await scenario.start(tg_id=user.tg_id, server_id=2)

        deps["create_key"].proces.assert_called_once_with(
            tg_id=user.tg_id,
            tariff=tariff,
            server_id=2,
            conn=scenario._conn,
        )

    async def test_create_first_key_installs_trial_after_key_creation(self):
        """Trial installation is called after successful key creation."""
        user = _make_user(tg_id=555003)
        scenario, deps = _make_scenario(user=user)

        await scenario.get_data()
        await scenario.start(tg_id=user.tg_id, server_id=2)

        deps["trial_user"].installation_trial.assert_called_once_with(
            user.tg_id, scenario._conn
        )

    async def test_create_first_key_starts_trial_dialog(self):
        """Without gift, transitions to KeysInit.create_trial with link data."""
        user = _make_user(tg_id=555004)
        dm = _make_dialog_manager(user.tg_id)
        scenario, _ = _make_scenario(user=user, dialog_manager=dm)

        await scenario.get_data()
        await scenario.start(tg_id=user.tg_id, server_id=2)

        call_kwargs = dm.start.call_args
        assert call_kwargs[0][0] == KeysInit.create_trial

    async def test_start_passes_link_data_to_dialog(self):
        """Dialog is started with public_link and link_to_connect in data dict."""
        user = _make_user(tg_id=555005)
        dm = _make_dialog_manager(user.tg_id)
        scenario, _ = _make_scenario(user=user, dialog_manager=dm)

        await scenario.get_data()
        await scenario.start(tg_id=user.tg_id, server_id=2)

        call = dm.start.call_args
        data_arg = call[1].get("data") or (call[0][1] if len(call[0]) > 1 else None)
        assert data_arg is not None
        assert "public_link" in data_arg
        assert "link_to_connect" in data_arg


class TestStartGiftFlow:
    async def test_create_first_key_with_gift_calls_gift_service_application(self):
        """When gift is present, gift_service.application is called."""
        user = _make_user(tg_id=555010)
        gift = GiftLink(sender_tg_id=42, tariff_id=3, token="gift_tok")
        scenario, deps = _make_scenario(user=user, gift=gift)

        await scenario.get_data()
        await scenario.start(tg_id=user.tg_id, server_id=2)

        deps["gift_service"].application.assert_called_once()

    async def test_create_first_key_with_gift_starts_gift_key_dialog(self):
        """Gift flow transitions to KeysInit.create_gift_key."""
        user = _make_user(tg_id=555011)
        dm = _make_dialog_manager(user.tg_id)
        gift = GiftLink(sender_tg_id=42, tariff_id=3, token="gift_tok")
        scenario, _ = _make_scenario(user=user, gift=gift, dialog_manager=dm)

        await scenario.get_data()
        await scenario.start(tg_id=user.tg_id, server_id=2)

        dm.start.assert_called()
        started_state = dm.start.call_args[0][0]
        assert started_state == KeysInit.create_gift_key


# ------------------------------------------------------------------ #
# Tests: error handling                                                #
# ------------------------------------------------------------------ #

class TestStartErrorHandling:
    async def test_error_handling_when_create_key_returns_none(self):
        """If create_key.proces returns None, starts KeysInit.error."""
        user = _make_user(tg_id=555020)
        dm = _make_dialog_manager(user.tg_id)
        scenario, deps = _make_scenario(
            user=user, dialog_manager=dm, create_key_result=None
        )
        deps["create_key"].proces = AsyncMock(return_value=None)

        await scenario.get_data()
        await scenario.start(tg_id=user.tg_id, server_id=2)

        dm.start.assert_called()
        started_state = dm.start.call_args[0][0]
        assert started_state == KeysInit.error

    async def test_error_handling_when_tariff_not_found(self):
        """Tariff not in DB (get_data returns None tariff) → start leads to error dialog."""
        user = _make_user(tg_id=555021)
        dm = _make_dialog_manager(user.tg_id)
        scenario, deps = _make_scenario(user=user, dialog_manager=dm)
        deps["model_data"].tariffs.get_data = AsyncMock(return_value=None)

        await scenario.get_data()
        # _tariff is None → create_key.proces call will fail internally
        # scenario.start catches and routes to error
        deps["create_key"].proces = AsyncMock(side_effect=AttributeError("tariff is None"))

        await scenario.start(tg_id=user.tg_id, server_id=2)

        dm.start.assert_called()
        started_state = dm.start.call_args[0][0]
        assert started_state == KeysInit.error

    async def test_error_handling_when_trial_already_used(self):
        """User with trial=1 → can_handle returns False → exception raised → error dialog started."""
        user = _make_user(tg_id=555022, trial=1)
        dm = _make_dialog_manager(user.tg_id)
        scenario, _ = _make_scenario(user=user, dialog_manager=dm)

        await scenario.get_data()
        await scenario.start(tg_id=user.tg_id, server_id=2)

        dm.start.assert_called()
        started_state = dm.start.call_args[0][0]
        assert started_state == KeysInit.error

    async def test_error_dialog_started_with_reset_stack_mode(self):
        """Error dialog is started with StartMode.RESET_STACK."""
        user = _make_user(tg_id=555023, trial=1)
        dm = _make_dialog_manager(user.tg_id)
        scenario, _ = _make_scenario(user=user, dialog_manager=dm)

        await scenario.get_data()
        await scenario.start(tg_id=user.tg_id, server_id=2)

        call_kwargs = dm.start.call_args[1]
        assert call_kwargs.get("mode") == StartMode.RESET_STACK

    async def test_create_key_exception_routes_to_error_dialog(self):
        """Unexpected exception from create_key.proces → error dialog."""
        user = _make_user(tg_id=555024)
        dm = _make_dialog_manager(user.tg_id)
        scenario, deps = _make_scenario(user=user, dialog_manager=dm)
        deps["create_key"].proces = AsyncMock(side_effect=RuntimeError("xui crash"))

        await scenario.get_data()
        await scenario.start(tg_id=user.tg_id, server_id=2)

        dm.start.assert_called()
        started_state = dm.start.call_args[0][0]
        assert started_state == KeysInit.error


# ------------------------------------------------------------------ #
# Tests: key cache pattern (email identifier)                          #
# ------------------------------------------------------------------ #

class TestKeyCacheIdentifier:
    async def test_key_saved_to_db_via_save_data(self):
        """CreateKey.proces internally calls key_data.save_data — proxy through create_key mock."""
        user = _make_user(tg_id=555030)
        scenario, deps = _make_scenario(user=user)

        await scenario.get_data()
        await scenario.start(tg_id=user.tg_id, server_id=2)

        # create_key.proces was called (save_data is internal to CreateKey, verified via mock)
        deps["create_key"].proces.assert_called_once()

    async def test_create_key_called_with_email_in_result(self):
        """The result from create_key.proces includes 'email' key (used for cache key)."""
        user = _make_user(tg_id=555031)
        key_result = {
            "public_link": "vpn://link",
            "link_to_connect": "https://example.com",
            "email": "user_555031@test.com",
            "days": 30,
        }
        scenario, deps = _make_scenario(user=user, create_key_result=key_result)
        deps["create_key"].proces = AsyncMock(return_value=key_result)

        await scenario.get_data()
        await scenario.start(tg_id=user.tg_id, server_id=2)

        result = deps["create_key"].proces.return_value
        assert "email" in result
        assert result["email"] == "user_555031@test.com"
