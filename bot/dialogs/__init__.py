from aiogram import Router

from dialogs.registry import DialogRegistry
from dialogs.windows import ALL_WINDOW_CONFIGS
from services.container.app import get_container


async def setup_dialog_router() -> Router:
    container = await get_container()
    registry = DialogRegistry(container)

    # Пользовательские диалоги через WindowFactory
    registry.add_from_configs(ALL_WINDOW_CONFIGS)

    return registry.build_router()
