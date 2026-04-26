from dialogs.conditions import compile_condition


def test_compile_condition_trial():
    condition = compile_condition("trial")
    assert condition({"trial": True}, None, None) is True
    assert condition({"trial": False}, None, None) is False
    assert condition({}, None, None) is False


def test_compile_condition_not_trial_tariff():
    condition = compile_condition("not_trial_tariff")
    assert condition({"is_trial": False}, None, None) is True
    assert condition({"is_trial": True}, None, None) is False
    assert condition({}, None, None) is True  # default value


def test_compile_condition_check_key():
    condition = compile_condition("check_key")
    assert condition({"count_key": 5}, None, None) is True
    assert condition({"count_key": 0}, None, None) is False
    assert condition({}, None, None) is False


def test_compile_condition_is_admin():
    condition = compile_condition("is_admin")
    assert condition({"is_admin": True}, None, None) is True
    assert condition({"is_admin": False}, None, None) is False
    assert condition({}, None, None) is False


def test_compile_condition_token():
    condition = compile_condition("token")
    assert condition({"token": "abc123"}, None, None) is True
    assert condition({"token": ""}, None, None) is False
    assert condition({}, None, None) is False


def test_compile_condition_check_usage_link():
    condition = compile_condition("check_usage_link")
    assert condition({"referral_link": "https://t.me/test"}, None, None) is True
    assert condition({"referral_link": ""}, None, None) is False
    assert condition({}, None, None) is False


def test_compile_condition_state_key_manager():
    condition = compile_condition("state_key_manager")
    assert condition({"flow": "key_manager"}, None, None) is True
    assert condition({"flow": "other"}, None, None) is False
    assert condition({}, None, None) is False


def test_compile_condition_state_search():
    condition = compile_condition("state_search")
    assert condition({"flow": "search"}, None, None) is True
    assert condition({"flow": "other"}, None, None) is False
    assert condition({}, None, None) is False


def test_compile_condition_unknown():
    condition = compile_condition("unknown_condition")
    assert condition({"any_data": "value"}, None, None) is True  # default behavior
