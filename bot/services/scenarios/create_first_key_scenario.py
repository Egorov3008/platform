from typing import Dict, Any, Optional

import asyncpg
from aiogram_dialog import DialogManager, StartMode

from config import DEFAULT_PRICING_PLAN
from logger import logger
from models import Tariff, User, GiftLink
from services.cache.key_manager import CacheKeyManager
from services.cache.service import CacheService
from services.core.data.service import ServiceDataModel
from services.core.gift import GiftLinkProvider
from services.core.keys.utils.create_key import CreateKey
from services.core.user.utils.trial import TrialService
from services.scenarios.factory_scenario import ScenarioFactory
from states.key import KeysInit


class CreateFerstKeyScenario(ScenarioFactory):
    """Оркестратор сценария создания ключа."""

    def __init__(
        self,
        cache: CacheService,
        model_data: ServiceDataModel,
        create_key: CreateKey,
        gift_service: GiftLinkProvider,
        trial_user: TrialService,
        conn: asyncpg.Pool,
        dialog_manager: DialogManager = None,
    ):

        super().__init__(dialog_manager)
        self.cache = cache
        self.tariff_data = model_data.tariffs
        self.user_data = model_data.users
        self.dialog_manager = dialog_manager
        self.create_key = create_key
        self.gift_service = gift_service
        self.trial_user = trial_user

        self._conn: asyncpg.Pool = conn
        self._tariff: Optional[Tariff] = None
        self._user: Optional[User] = None
        self._gift: Optional[GiftLink] = None

    async def can_handle(self):

        await self.get_data()
        logger.info(
            "Проверка возможности обработки сценария",
            user_id=self._user.tg_id if self._user else None,
        )
        return self._user.trial == 0

    async def start(self, tg_id: int, server_id: int):

        try:
            if not await self.can_handle():
                logger.warning(
                    "Пользователь уже использовал пробный период",
                    user_id=self._user.tg_id,
                )
                raise Exception("Пользователь использовал пробный период")

            logger.info(
                "Начало процесса создания первого ключа", user_id=self._user.tg_id
            )
            logger.info(
                "Установка пробного периода для пользователя", user_id=self._user.tg_id
            )
            await self.trial_user.installation_trial(self._user.tg_id, self._conn)

            logger.info(
                "Создание ключа для пользователя",
                user_id=self._user.tg_id,
                tariff_id=self._tariff.id if self._tariff else None,
            )
            key_data = await self.create_key.proces(
                tg_id=self._user.tg_id,
                tariff=self._tariff,
                server_id=self._user.server_id,
                conn=self._conn,
            )
            if not key_data:
                logger.error("Не удалось создать ключ", user_id=self._user.tg_id)
                raise RuntimeError("Не удалось создать ключ")

            data = {
                "public_link": key_data.get("public_link"),
                "link_to_connect": key_data.get("link_to_connect"),
            }

            if self._gift:
                await self.gift_service.application(
                    self._conn, self._gift, self._user.tg_id, key_data.get("email")
                )

                logger.info(
                    "Запуск диалога создания подарочного ключа",
                    user_id=self._user.tg_id,
                )
                await self.dialog_manager.start(KeysInit.create_gift_key, data=data)
                return

            logger.info(
                "Запуск диалога создания пробного ключа", user_id=self._user.tg_id
            )
            await self.dialog_manager.start(KeysInit.create_trial, data=data)

        except Exception as e:
            logger.error(
                "Ошибка при создании первого ключа",
                error_type=type(e).__name__,
                error_msg=str(e),
                user_id=self._user.tg_id if self._user else None,
            )
            if self.dialog_manager:
                await self.dialog_manager.start(
                    KeysInit.error, mode=StartMode.RESET_STACK
                )

    async def get_data(self):
        """Получает данные из кэша и мидлвари."""
        logger.debug("Получение данных для сценария")
        if not self.dialog_manager:
            raise ValueError("DialogManager не инициализирован")
        user_id = self.dialog_manager.event.from_user.id
        self._user: Optional[User] = await self.user_data.get_data(user_id)
        temporary_data: Dict[str, Any] = await self.cache.gifts.temporary_get(
            CacheKeyManager.gift_activation(user_id)
        )

        # Проверяем 'gift' в temporary_data
        self._gift = temporary_data.get("gift") if temporary_data else None

        # Если temporary_data нет или в нём нет tariff_id, используем значение по умолчанию
        default_plan_id = int(DEFAULT_PRICING_PLAN) if DEFAULT_PRICING_PLAN else 10
        tariff_id = self._gift.tariff_id if self._gift else default_plan_id

        logger.debug("Получаю тариф", user_id=self._user.tg_id, tariff_id=tariff_id)

        self._tariff = await self.tariff_data.get_data(tariff_id)
        self._conn = self.dialog_manager.middleware_data.get("session")
