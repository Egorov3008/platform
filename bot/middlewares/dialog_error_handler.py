# middlewares/dialog_error_handler.py
import random
from typing import Callable, Dict, Any

from aiogram import BaseMiddleware
from aiogram.types import TelegramObject
from aiogram_dialog.api.exceptions import UnknownIntent, OutdatedIntent
from dialogs.messages.users.error_msg.bot_errors import error_messages
from logger import logger


class DialogExceptionHandlerMiddleware(BaseMiddleware):
    async def __call__(
        self,
        handler: Callable[[TelegramObject, Dict[Any, Any]], Any],
        event: TelegramObject,
        data: Dict[Any, Any],
    ) -> Any:
        try:
            return await handler(event, data)
        except UnknownIntent as e:
            logger.warning(
                "UnknownIntent: диалог сброшен",
                error_message=str(e),
                user_id=data.get("event_from_user", {}).id if data.get("event_from_user") else None
            )

            bot = data.get("bot")
            user_id = data.get("event_from_user").id
            try:
                await bot.send_message(
                    user_id,
                    random.choice(error_messages),
                )

            except Exception as send_err:
                logger.error(
                    "Не удалось отправить сообщение о сбросе диалога",
                    error_type=type(send_err).__name__,
                    error_message=str(send_err)
                )

        except OutdatedIntent as e:
            # Обработка устаревшего intent (пользователь нажал кнопку на старом сообщении)
            logger.warning(
                "OutdatedIntent: стек устарел",
                error_message=str(e),
                user_id=data.get("event_from_user", {}).id if data.get("event_from_user") else None
            )

            bot = data.get("bot")
            user_id = data.get("event_from_user").id if data.get("event_from_user") else None

            if user_id:
                try:
                    await bot.send_message(
                        user_id,
                        "⚠️ Меню устарело. Пожалуйста, откройте меню заново командой /profile",
                    )
                except Exception as send_err:
                    logger.error(
                        "Не удалось отправить сообщение об устаревшем меню",
                        error_type=type(send_err).__name__,
                        error_message=str(send_err)
                    )

            # Не пробрасываем исключение дальше, чтобы не ломать общий поток
            return

        except Exception:
            logger.exception("Unexpected error in DialogExceptionHandlerMiddleware")
            raise
