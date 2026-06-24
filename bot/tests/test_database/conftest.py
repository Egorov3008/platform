import pytest


@pytest.fixture
def mock_user(user):
    return user


@pytest.fixture
def mock_key(key):
    return key


@pytest.fixture
def mock_server(server):
    return server


@pytest.fixture
def mock_payment(payment):
    return payment


@pytest.fixture
def mock_tariff(tariff):
    return tariff
