from aiogram_dialog import DialogManager, StartMode

from api.backend_client import BackendAPIClient
from logger import logger
from services.scenarios.factory_scenario import ScenarioFactory
from states.key import KeysInit


def _read_trial(user) -> int:
    """Безопасно извлекает поле trial из dict или dataclass-объекта."""
    if isinstance(user, dict):
        return user.get("trial", 1)
    return getattr(user, "trial", 1)


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
        """Сценарий применим только для зарегистрированного пользователя,
        у которого пробный период ещё не использован.

        Возвращает False (не наш сценарий), если:
        - нет DialogManager;
        - пользователь не зарегистрирован (get_user() == None) — в этом случае
          нужно сначала отработать регистрацию, а уже потом создавать ключ;
        - у пользователя уже trial=1.
        """
        if not self.dialog_manager:
            return False
        user_id = self.dialog_manager.event.from_user.id
        user = await self.backend.get_user(user_id)
        if not user:
            logger.info(
                "Сценарий не применим: пользователь не зарегистрирован",
                user_id=user_id,
            )
            return False
        return _read_trial(user) == 0

    async def start(self, tg_id: int, server_id: int):
        try:
            # Проверяем, зарегистрирован ли пользователь.
            # Если нет — сначала регистрируем (auto-register), затем продолжаем.
            user = await self.backend.get_user(tg_id)
            if not user:
                logger.warning(
                    "Пользователь не зарегистрирован — выполняю авто-регистрацию",
                    user_id=tg_id,
                )
                # DialogManager нужен для получения данных отправителя (username, name, ...)
                if not self.dialog_manager or not self.dialog_manager.event.from_user:
                    logger.error(
                        "Невозможно зарегистрировать пользователя: нет DialogManager",
                        user_id=tg_id,
                    )
                    if self.dialog_manager:
                        await self.dialog_manager.start(
                            KeysInit.error, mode=StartMode.RESET_STACK
                        )
                    return

                from_user = self.dialog_manager.event.from_user
                registered = await self.backend.admin_register_user(
                    {
                        "tg_id": tg_id,
                        "username": from_user.username,
                        "first_name": from_user.first_name,
                        "last_name": from_user.last_name,
                        "language_code": from_user.language_code,
                        "server_id": server_id,
                    }
                )
                if not registered or not registered.get("tg_id"):
                    logger.error(
                        "Не удалось зарегистрировать пользователя",
                        user_id=tg_id,
                    )
                    if self.dialog_manager:
                        await self.dialog_manager.start(
                            KeysInit.error, mode=StartMode.RESET_STACK
                        )
                    return
                user = registered

            if _read_trial(user) != 0:
                logger.warning(
                    "Пользователь уже использовал пробный период",
                    user_id=tg_id,
                )
                if self.dialog_manager:
                    await self.dialog_manager.start(
                        KeysInit.error, mode=StartMode.RESET_STACK
                    )
                return

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
                if self.dialog_manager:
                    await self.dialog_manager.start(
                        KeysInit.error, mode=StartMode.RESET_STACK
                    )
                return

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
