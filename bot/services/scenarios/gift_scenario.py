import traceback
from typing import Any, Optional

from datetime import timedelta
from aiogram_dialog import StartMode, DialogManager

from logger import logger
from models import GiftLink
from services.cache.key_manager import CacheKeyManager
from services.cache.service import CacheService
from services.core.data.service import ServiceDataModel
from services.core.user.utils.saver import SeverUser
from services.scenarios.factory_scenario import ScenarioFactory
from states.gift import GiftStates
from states.instruction import Instruction


class GiftActivationScenario(ScenarioFactory):
    """
    Оркестратор сценария активации подарка.
    Управляет потоком: проверка → активация → выдача ключа.
    """

    def __init__(
        self,
        dialog_manager: DialogManager,
        service_model: ServiceDataModel,
        saver: SeverUser,
        cache: CacheService,
    ):
        super().__init__(dialog_manager)
        self.service_model = service_model
        self.saver = saver
        self.cache = cache

        # Извлекаем зависимости в конструкторе
        self._gift_data = service_model.gifts
        self._token: Optional[str] = None
        self._type: Optional[str] = None
        self._conn: Optional[Any] = None

    async def can_handle(self) -> bool:
        await self.get_data()
        return self._token is not None and self._type is not None

    async def start(self):
        """Запуск сценария активации подарка."""
        await self.get_data()

        user_id = self.dialog_manager.event.from_user.id
        try:
            # 1. Получаем GiftLink по токену
            gift: Optional[GiftLink] = await self._get_gift(self._token)

            # 2. Проверяем, уже ли использован
            if not await self._process_checked_gift(gift):
                # 3. Активируем подарок
                await self._process_success(user_id, gift)

        except Exception as e:
            logger.error(
                "Активация подарка не удалась",
                error=str(e),
                user_id=user_id,
                traceback=traceback.format_exc(),
            )
            await self.dialog_manager.start(GiftStates.error)

    async def _get_gift(self, token) -> Optional[GiftLink]:
        """Получаем GiftLink по токену."""
        if not token:
            raise ValueError("Токен не передан")
        return await self._gift_data.get_by(token=token)

    async def _process_checked_gift(self, gift_link: Optional[GiftLink]) -> Any:
        """Обработка уже использованного или ненайденного подарка."""
        if not gift_link:
            await self.dialog_manager.start(
                GiftStates.error, mode=StartMode.RESET_STACK
            )
            return True
        if not gift_link.is_redeemable():
            await self.dialog_manager.start(
                GiftStates.already_used, mode=StartMode.RESET_STACK
            )
            return True
        return False

    async def get_data(self):
        """Извлекает данные из middleware_data."""
        registration_result = self.dialog_manager.middleware_data.get(
            "registration_result"
        )
        if not registration_result:
            return

        self._token = registration_result.get("token")
        self._type = registration_result.get("type")
        self._conn = self.dialog_manager.middleware_data.get("session")

    async def _process_success(self, user_id: int, gift: GiftLink):
        """Обработка успешной активации подарка."""

        user = await self.saver.register_user(self._conn, tg_id=user_id, server_id=2)

        # Добавляем пользователя в кеш после создания в БД
        await self.cache.users.set(CacheKeyManager.user(user_id), user)

        data = {"gift_status": True, "gift": gift}

        await self.cache.gifts.temporary_set(
            CacheKeyManager.gift_activation(user_id), ttl=timedelta(minutes=30), **data
        )
        await self.dialog_manager.start(
            Instruction.choosing_device, mode=StartMode.RESET_STACK
        )
