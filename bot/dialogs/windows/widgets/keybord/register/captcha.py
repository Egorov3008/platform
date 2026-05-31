import random

from aiogram.exceptions import TelegramAPIError
from aiogram.types import Message
from aiogram_dialog import DialogManager, StartMode
from aiogram_dialog.widgets.input import TextInput

from api.backend_client import BackendAPIClient
from config import ADMIN_ID
from dialogs.windows.base import KeyboardBuilder
from logger import logger
from states.main import MainMenu


class CaptchaKeyboard(KeyboardBuilder):
    """Клавиатура капчи: TextInput для ввода ответа на арифметический пример."""

    async def _on_answer_entered(
        self,
        message: Message,
        widget: TextInput,
        dialog_manager: DialogManager,
        text: str,
    ) -> None:
        """Обработчик ввода ответа на капчу."""
        correct_answer = dialog_manager.dialog_data.get("captcha_answer")

        try:
            user_answer = int(text.strip())
        except (ValueError, AttributeError):
            self._generate_captcha(dialog_manager)
            await message.answer("❌ Введите целое число. Попробуйте ещё раз.")
            return

        if user_answer == correct_answer:
            await self._auto_register(message, dialog_manager)
        else:
            self._generate_captcha(dialog_manager)
            await message.answer("❌ Неверный ответ. Попробуйте ещё раз.")

    @staticmethod
    def _generate_captcha(dialog_manager: DialogManager) -> None:
        """Генерирует новый арифметический пример и сохраняет ответ в dialog_data."""
        a = random.randint(1, 20)
        b = random.randint(1, 20)
        dialog_manager.dialog_data["captcha_question"] = f"{a} + {b} = ?"
        dialog_manager.dialog_data["captcha_answer"] = a + b

    async def _auto_register(
        self, message: Message, dialog_manager: DialogManager
    ) -> None:
        """Авто-регистрация пользователя через backend API после капчи."""
        tg_id = message.from_user.id
        try:
            container = dialog_manager.middleware_data.get("container")
            backend: BackendAPIClient = container.resolve(BackendAPIClient)

            from_user = message.from_user
            payload = {
                "tg_id": tg_id,
                "username": from_user.username if from_user else None,
                "first_name": from_user.first_name if from_user else None,
                "last_name": from_user.last_name if from_user else None,
                "language_code": from_user.language_code if from_user else None,
                "server_id": 2,
            }

            new_user = await backend.admin_register_user(payload)
            if not new_user or not new_user.get("tg_id"):
                raise RuntimeError("Backend registration failed or returned empty user")

            logger.info(
                "Пользователь авто-зарегистрирован через капчу (backend)",
                tg_id=tg_id,
            )

            await self._notify_admins(message)
            await dialog_manager.start(MainMenu.welcome, mode=StartMode.RESET_STACK)

        except Exception as e:
            logger.error(
                "Ошибка при авто-регистрации через капчу",
                tg_id=tg_id,
                error_type=type(e).__name__,
                error_message=str(e),
                exc_info=True,
            )
            await message.answer(
                "❌ Произошла ошибка при регистрации. Попробуйте позже или напишите /start"
            )

    @staticmethod
    async def _notify_admins(message: Message) -> None:
        """Отправляет информационное уведомление админам о новом пользователе."""
        from_user = message.from_user
        tg_id = from_user.id
        name = from_user.full_name or ""
        username = f"@{from_user.username}" if from_user.username else "нет"

        admin_text = (
            "👤 <b>Новая регистрация</b>\n\n"
            f"🆔 ID: <code>{tg_id}</code>\n"
            f"👤 Имя: {name}\n"
            f"🔗 Username: {username}"
        )
        for admin_id in ADMIN_ID:
            try:
                await message.bot.send_message(
                    chat_id=admin_id,
                    text=admin_text,
                    parse_mode="HTML",
                )
            except TelegramAPIError:
                pass

    def build(self):
        return (
            TextInput(
                id="captcha_input",
                type_factory=str,
                on_success=self._on_answer_entered,
            ),
        )
