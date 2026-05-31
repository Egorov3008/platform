import traceback
from typing import Optional

from aiogram_dialog import StartMode, DialogManager

from api.backend_client import BackendAPIClient
from logger import logger
from services.scenarios.factory_scenario import ScenarioFactory
from states.gift import GiftStates
from states.instruction import Instruction


class GiftActivationScenario(ScenarioFactory):
    """
    Оркестратор сценария активации подарка через backend API.
    Управляет потоком: проверка → регистрация → выбор устройства.
    """

    def __init__(
        self,
        dialog_manager: DialogManager,
        backend_client: BackendAPIClient,
    ):
        super().__init__(dialog_manager)
        self.backend = backend_client
        self._token: Optional[str] = None
        self._type: Optional[str] = None

    async def can_handle(self) -> bool:
        await self.get_data()
        return self._token is not None and self._type is not None

    async def start(self):
        """Запуск сценария активации подарка."""
        await self.get_data()

        user_id = self.dialog_manager.event.from_user.id
        try:
            if not self._token:
                await self.dialog_manager.start(
                    GiftStates.error, mode=StartMode.RESET_STACK
                )
                return

            # 1. Проверяем gift по токену через backend
            gift = await self.backend.get_gift_by_token(self._token)
            if not gift:
                await self.dialog_manager.start(
                    GiftStates.error, mode=StartMode.RESET_STACK
                )
                return

            # 2. Проверяем, не использован ли уже
            if gift.get("redeemed_at") or gift.get("recipient_tg_id"):
                await self.dialog_manager.start(
                    GiftStates.already_used, mode=StartMode.RESET_STACK
                )
                return

            # 3. Убеждаемся, что пользователь зарегистрирован
            user = await self.backend.get_user(user_id)
            if not user:
                from_user = self.dialog_manager.event.from_user
                payload = {
                    "tg_id": user_id,
                    "username": getattr(from_user, "username", None),
                    "first_name": getattr(from_user, "first_name", None),
                    "last_name": getattr(from_user, "last_name", None),
                    "language_code": getattr(from_user, "language_code", None),
                    "server_id": 2,
                }
                user = await self.backend.admin_register_user(payload)

            # 4. Переходим к выбору устройства, передавая gift_token
            await self.dialog_manager.start(
                Instruction.choosing_device,
                mode=StartMode.RESET_STACK,
                data={"gift_token": self._token},
            )

        except Exception as e:
            logger.error(
                "Активация подарка не удалась",
                error=str(e),
                user_id=user_id,
                traceback=traceback.format_exc(),
            )
            await self.dialog_manager.start(GiftStates.error)

    async def get_data(self):
        """Извлекает данные из middleware_data."""
        registration_result = self.dialog_manager.middleware_data.get(
            "registration_result"
        )
        if not registration_result:
            return

        self._token = registration_result.get("token")
        self._type = registration_result.get("type")
