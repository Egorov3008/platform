from aiogram.types import CallbackQuery
from aiogram_dialog import DialogManager
from aiogram_dialog.widgets.kbd import Column, Url, Button, SwitchTo, Keyboard
from aiogram_dialog.widgets.text import Const

from api.backend_client import BackendAPIClient
from dialogs.windows.base import KeyboardBuilder
from services.scenarios.create_first_key_scenario import CreateFerstKeyScenario
from states.instruction import Instruction


class BaseDeviceKeyboard(KeyboardBuilder):
    """Базовый клавиатурный билдер для окон выбора устройства."""

    _download_url: str
    _download_label: str
    _next_btn_id: str

    def __init__(
        self, backend_client: BackendAPIClient, create_trial_key: CreateFerstKeyScenario
    ):
        self.backend = backend_client
        self.create_trial_key = create_trial_key

    async def _on_next_step(
        self, callback: CallbackQuery, button: Button, dialog_manager: DialogManager
    ):
        tg_id = dialog_manager.event.from_user.id
        user = await self.backend.get_user(tg_id)
        server_id = user.get("server_id", 2) if user else 2
        self.create_trial_key.dialog_manager = dialog_manager
        await self.create_trial_key.start(tg_id, server_id)

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
