from unittest.mock import AsyncMock, MagicMock

import pytest

from services.core.data.service import ServiceDataModel
from services.core.keys.utils.calculator import ExpiryCalculator
from services.core.keys.utils.create_key import CreateKey
from services.core.keys.utils.formtion import FormationKey
from services.core.keys.utils.renewal import KeyRenewal
from services.core.keys.utils.updating import KeyUpdater
from services.core.keys.utils.reset import KeyResetter


@pytest.fixture
def mock_model_data():
    model_data = MagicMock(spec=ServiceDataModel)
    model_data.keys = AsyncMock()
    model_data.users = AsyncMock()
    model_data.servers = AsyncMock()
    return model_data


@pytest.fixture
def create_key(mock_model_data, mock_xui_session, expiry_calculator):
    formation = AsyncMock(spec=FormationKey)
    ck = CreateKey(
        model_data=mock_model_data,
        xui_session=mock_xui_session,
        expiry=expiry_calculator,
        formation=formation,
    )
    ck.cache_data = AsyncMock()
    return ck


@pytest.fixture
def cache_data():
    return AsyncMock()


@pytest.fixture
def formation_key(mock_cache, expiry_calculator):
    connected_data = AsyncMock()
    return FormationKey(
        cache=mock_cache,
        connected_data=connected_data,
        expiry=expiry_calculator,
    )


@pytest.fixture
def renewal_key(mock_model_data, mock_xui_session, expiry_calculator, mock_cache):
    refresh_key = KeyUpdater(expiry_calculator=expiry_calculator)
    resetter = KeyResetter(cache_service=mock_cache)
    return KeyRenewal(
        model_data=mock_model_data,
        xui_session=mock_xui_session,
        refresh_key=refresh_key,
        resetter=resetter,
    )
