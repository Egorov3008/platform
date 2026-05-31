from aiogram_dialog import DialogManager, StartMode

from api.backend_client import BackendAPIClient
from logger import logger
from services.scenarios.factory_scenario import ScenarioFactory
from states.key import KeysInit


class CreateFerstKeyScenario(ScenarioFactory):
    """Оркестратор сценария создания первого ключа через backend API."""

    def __init__(
        self,
        backend_client: BackendAPIClient,
        dialog_manager: DialogManager = None,
    ):
        super().__init__(dialog_manager)
        self.backend = backend_client

    async def get_data(self, **kwargs):
        """Загружает данные пользователя из backend, если DialogManager доступен."""
        if not self.dialog_manager:
            return None
        user_id = self.dialog_manager.event.from_user.id
        return await self.backend.get_user(user_id)

    async def can_handle(self) -> bool:
        if not self.dialog_manager:
            return False
        user_id = self.dialog_manager.event.from_user.id
        user = await self.backend.get_user(user_id)
        logger.info(
            "Проверка возможности обработки сценария",
            user_id=user_id,
        )
        return user is not None and user.get("trial", 1) == 0

    async def start(self, tg_id: int, server_id: int):
        try:
            if not await self.can_handle():
                logger.warning(
                    "Пользователь уже использовал пробный период",
                    user_id=tg_id,
                )
                raise Exception("Пользователь использовал пробный период")

            logger.info(
                "Начало процесса создания первого ключа через backend",
                user_id=tg_id,
            )

            gift_token = None
            if self.dialog_manager:
                gift_token = self.dialog_manager.dialog_data.get("gift_token")

            key = await self.backend.create_trial_key(tg_id, gift_token=gift_token)
            if not key:
                logger.error("Не удалось создать ключ", user_id=tg_id)
                raise RuntimeError("Не удалось создать ключ")

            data = {
                "public_link": key.public_link or key.key,
                "link_to_connect": key.link_to_connect or key.key,
            }

            if gift_token:
                logger.info(
                    "Запуск диалога создания подарочного ключа",
                    user_id=tg_id,
                )
                await self.dialog_manager.start(KeysInit.create_gift_key, data=data)
                return

            logger.info(
                "Запуск диалога создания пробного ключа", user_id=tg_id
            )
            await self.dialog_manager.start(KeysInit.create_trial, data=data)

        except Exception as e:
            logger.error(
                "Ошибка при создании первого ключа",
                error_type=type(e).__name__,
                error_msg=str(e),
                user_id=tg_id,
            )
            if self.dialog_manager:
                await self.dialog_manager.start(
                    KeysInit.error, mode=StartMode.RESET_STACK
                )
