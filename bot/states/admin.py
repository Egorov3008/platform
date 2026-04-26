from aiogram.fsm.state import StatesGroup, State


class AdminManager(StatesGroup):
    main = State()
    static_user = State()
    search = State()
    confirmation_deletion_keys = State()
    input_url = State()
    key_list = State()
    key_details = State()
    dashboard = State()
    key_stats = State()
    payment_stats = State()


class AdminSearchManagementSG(StatesGroup):
    main = State()
    search_tg_id = State()
    search_username = State()
    search_email = State()
    profile_user = State()


class AdminMassMailing(StatesGroup):
    receiving_message = State()
    confirmation = State()


class AdminUserManagement(StatesGroup):
    profile_user = State()


class AdminKeyDeleteSG(StatesGroup):
    confirm = State()


class AdminKeyChangeDateSG(StatesGroup):
    pick_date = State()
    confirm = State()


class AdminKeyChangeTariffSG(StatesGroup):
    pick_tariff = State()
    confirm = State()


class AdminUserDeleteSG(StatesGroup):
    confirm = State()


class AdminGenerateKeySG(StatesGroup):
    input_tg_id = State()
    choosing_inbound = State()
    choosing_tariff = State()
    confirm_generate = State()
    result = State()


class AdminUserCleanupSG(StatesGroup):
    review = State()
    confirm = State()


class AdminMassRenewal(StatesGroup):
    select_segment = State()
    input_days = State()
    preview = State()


