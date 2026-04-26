from aiogram.types import CallbackQuery
from aiogram_dialog import DialogManager
from aiogram_dialog.widgets.kbd import Column, Url, Button, SwitchTo, Keyboard
from aiogram_dialog.widgets.text import Const

from dialogs.windows.base import KeyboardBuilder
from models import User
from services.core.data.service import ServiceDataModel
from services.scenarios.create_first_key_scenario import CreateFerstKeyScenario
from states.instruction import Instruction


class BaseDeviceKeyboard(KeyboardBuilder):
    """Базовый клавиатурный билдер для окон выбора устройства."""

    _download_url: str
    _download_label: str
    _next_btn_id: str

    def __init__(
        self, model_service: ServiceDataModel, create_trial_key: CreateFerstKeyScenario
    ):
        self.user_service = model_service.users
        self.create_trial_key = create_trial_key

    async def _on_next_step(
        self, callback: CallbackQuery, button: Button, dialog_manager: DialogManager
    ):
        tg_id = dialog_manager.event.from_user.id
        user: User = await self.user_service.get_data(tg_id)
        self.create_trial_key.dialog_manager = dialog_manager
        await self.create_trial_key.start(tg_id, user.server_id)

    def build(self) -> Keyboard:
        return Column(
            Url(Const(self._download_label), url=Const(self._download_url)),
            Button(
                Const("Следующий шаг ▶️"),
                id=self._next_btn_id,
                on_click=self._on_next_step,
            ),
            SwitchTo(
                Const("Назад ↩️"),
                id=f"back_{self._next_btn_id}",
                state=Instruction.choosing_device,
            ),
        )
