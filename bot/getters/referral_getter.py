from aiogram_dialog import DialogManager


async def partner_static_getter(dialog_manager: DialogManager, **kwargs):
    """гетер для формирвоания окна партнерской программы пользователя"""
    tg_id = dialog_manager.event.from_user.id
