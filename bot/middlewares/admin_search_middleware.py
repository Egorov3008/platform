from typing import Callable, Dict, Any, Awaitable

from aiogram import BaseMiddleware
from aiogram.types import Update

from config import ADMIN_ID
from logger import logger


class AdminSearchMiddleware(BaseMiddleware):
    """
    Middleware для обработки ссылок поиска пользователя администратором.

    Перехватывает команду /start с параметром формата `search_{tg_id}`.
    Если переходящий пользователь является администратором — парсит tg_id и
    кладёт его в data["admin_search_tg_id"], чтобы хендлер /start мог
    запустить состояние AdminSearchManagementSG.search_tg_id.

    Для обычных пользователей ссылка игнорируется, поток продолжается штатно.
    """

    PREFIX = "search_"

    async def __call__(
        self,
        handler: Callable[[Update, Dict[str, Any]], Awaitable[Any]],
        event: Update,
        data: Dict[str, Any],
    ) -> Any:
        # Пробуем распарсить параметр поиска только если есть пользователь
        user = data.get("event_from_user")
        if user and self._is_admin(user.id):
            search_tg_id = self._extract_search_tg_id(event)
            if search_tg_id is not None:
                logger.info(
                    "Админ перешёл по ссылке поиска пользователя",
                    admin_id=user.id,
                    target_tg_id=search_tg_id,
                )
                data["admin_search_tg_id"] = search_tg_id

        return await handler(event, data)

    def _is_admin(self, user_id: int) -> bool:
        """Проверяет, является ли пользователь администратором."""
        return user_id in ADMIN_ID

    def _extract_search_tg_id(self, event: Update) -> int | None:
        """
        Извлекает tg_id из параметра ссылки формата `search_{tg_id}`.

        Возвращает int tg_id при успехе, None — если параметр отсутствует
        или имеет неверный формат.
        """
        message = getattr(event, "message", None) or getattr(
            event, "edited_message", None
        )
        if not message:
            return None

        text = getattr(message, "text", None) or ""
        if not text.startswith("/start"):
            return None

        parts = text.split()
        if len(parts) < 2:
            return None

        token = parts[1]
        if not token.startswith(self.PREFIX):
            return None

        raw_id = token[len(self.PREFIX):]
        try:
            tg_id = int(raw_id)
        except ValueError:
            logger.warning(
                "Некорректный формат tg_id в ссылке поиска",
                raw_token=token,
                raw_id=raw_id,
            )
            return None

        return tg_id
