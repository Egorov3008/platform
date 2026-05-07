from aiogram_dialog import Window, Dialog, StartMode
from aiogram_dialog.widgets.kbd import Start, Url, CopyText
from aiogram_dialog.widgets.text import Const, Format

from config import SUPPORT_CHAT_URL
from getters.gift_getter import getter_gift_main
from states.gift import GiftStates
from states.main import MainMenu

main_window = Window(
    Const(
        "🎁 <b>Подарите VIP-доступ другу!</b>\n\n"
        "Отправьте ему эту ссылку — и он получит <b>тариф «160»</b> на целый месяц\n"
        "🔋 <i>1 устройство, 100 ГБ трафика, максимальная скорость!</i>\n\n"
        "✅ Подарок активируется автоматически при регистрации\n"
        "⏰ Действует только для нового пользователя\n\n"
        "👇 Нажмите, чтобы скопировать ссылку и отправить другу:"
    ),
    CopyText(Const("📋 Скопировать ссылку"), copy_text=Format("{link}")),
    Start(Const("👤 В личный кабинет"), id="profile", state=MainMenu.main),
    state=GiftStates.main,
    getter=getter_gift_main,
)

error_window = Window(
    Const("❌ К сожалению, не удалось активировать подарок."),
    Const("Возможно, временные неполадки. Попробуйте позже."),
    Url(Const("💬 Обратиться в поддержку"), url=SUPPORT_CHAT_URL),
    Start(Const("👤 В личный кабинет"), id="profile", state=MainMenu.main),
    state=GiftStates.error,
)

not_found_window = Window(
    Const("🎁 Подарок не найден"),
    Const("Ссылка может быть неактивна или устарела."),
    Start(
        Const("В главное меню"),
        id="home",
        state=MainMenu.welcome,
        mode=StartMode.RESET_STACK,
    ),
    state=GiftStates.not_found,
)

already_used_window = Window(
    Const("🎁 Этот подарок уже был использован"),
    Const("Каждый подарок можно активировать только один раз."),
    Start(
        Const("В главное меню"),
        id="home",
        state=MainMenu.welcome,
        mode=StartMode.RESET_STACK,
    ),
    state=GiftStates.already_used,
)

dialog = Dialog(error_window, not_found_window, already_used_window, main_window)
