from aiogram_dialog import StartMode
from aiogram_dialog.widgets.kbd import Keyboard, Column, Url, Start
from aiogram_dialog.widgets.text import Const, Format

from config import SUPPORT_CHAT_URL
from dialogs.windows.base import KeyboardBuilder
from states import MainMenu


class PaymentFormKeyboard(KeyboardBuilder):
    """Билдер для формирования клавиатуры при оплате.

    Ручная кнопка «ПРОВЕРИТЬ СТАТУС ОПЛАТЫ» убрана: после оплаты ключ
    активируется автоматически (webhook YooKassa + фоновый sweep pending-платежей
    в backend каждые 15 мин), пользователю приходит уведомление. Если уведомление
    не пришло — поддержка (кнопка ниже).
    """

    def build(self) -> Keyboard:
        return Column(
            Url(Const(text="Перейти к оплате 💶"), url=Format("{confirmation_url}")),
            Url(Const("💬 Поддержка"), url=Const(SUPPORT_CHAT_URL)),
            Start(
                Const("Назад"),
                id="profile",
                state=MainMenu.main,
                mode=StartMode.RESET_STACK,
            ),
        )
