"""Обработка /start landing_<uid> — конвертация анонимного 24ч лендинг-ключа.

Сценарии (см. план transient-forging-shore.md):
  1. Новый юзер            → claim: перенос tg_id + продление на 7 дней (trial) → ключ
  2. Существующий юзер    → mark-converted: 24ч ключ живёт, предложение оплатить
  3. Тот же юзер повторно → идемпотентно (claim → already_claimed / mark → already)
  4. Чужой аккаунт        → already_claimed_other → «ключ уже привязан к другому»
"""
from typing import Any, Dict

from aiogram.types import Message
from aiogram_dialog import DialogManager, StartMode

from api.backend_client import BackendAPIClient
from logger import logger
from services.core.user.utils.auto_register import register_user_only
from states.key import KeysInit
from states.main import MainMenu
from states.tariff import Tariff


async def handle_landing_start(
    message: Message,
    dialog_manager: DialogManager,
    result_registration: Dict[str, Any],
) -> None:
    """Маршрутизация лендинг-конверсии по registration_result из middleware."""
    if not message.from_user:
        return

    tg_id = message.from_user.id
    landing_uid = result_registration.get("landing_uid")
    is_registered = result_registration.get("is_registered", False)

    if not landing_uid:
        logger.warning("Landing start без landing_uid", tg_id=tg_id)
        await dialog_manager.start(MainMenu.welcome, mode=StartMode.RESET_STACK)
        return

    container = dialog_manager.middleware_data.get("container")
    if not container:
        await dialog_manager.start(MainMenu.welcome, mode=StartMode.RESET_STACK)
        return
    backend: BackendAPIClient = container.resolve(BackendAPIClient)

    if not is_registered:
        await _handle_new_user(message, dialog_manager, backend, tg_id, landing_uid)
    else:
        await _handle_existing_user(message, dialog_manager, backend, tg_id, landing_uid)


async def _handle_new_user(
    message: Message,
    dialog_manager: DialogManager,
    backend: BackendAPIClient,
    tg_id: int,
    landing_uid: str,
) -> None:
    """Новый юзер: авто-регистрация → claim (перенос + продление) → окно ключа."""
    new_user = await register_user_only(message, dialog_manager)
    if not new_user:
        return  # register_user_only уже показал сообщение об ошибке

    claim = await backend.claim_landing_key(landing_uid, tg_id)
    if not claim:
        await message.answer(
            "❌ Не удалось привязать ключ. Попробуйте позже или нажмите /start"
        )
        await dialog_manager.start(MainMenu.welcome, mode=StartMode.RESET_STACK)
        return

    status = claim.get("status")
    if status in ("claimed", "already_claimed"):
        email = claim.get("email")
        if status == "claimed":
            await message.answer(
                "🎉 <b>Ваш ключ продлён на 7 дней и привязан к аккаунту!</b>\n"
                "Та же ссылка, что вы импортировали в Happ, продолжает работать — "
                "переимпортировать не нужно."
            )
        else:
            await message.answer("✅ Ваш ключ уже привязан к этому аккаунту.")
        if email:
            await dialog_manager.start(
                KeysInit.key, mode=StartMode.RESET_STACK, data={"email": email}
            )
        else:
            await dialog_manager.start(MainMenu.main, mode=StartMode.RESET_STACK)
    elif status == "already_claimed_other":
        await message.answer(
            "⚠️ Этот ключ уже привязан к другому аккаунту. "
            "Если это не ваш аккаунт — сгенерируйте новый ключ на лендинге."
        )
        await dialog_manager.start(MainMenu.welcome, mode=StartMode.RESET_STACK)
    else:
        logger.warning("Неизвестный статус claim", status=status, tg_id=tg_id)
        await dialog_manager.start(MainMenu.welcome, mode=StartMode.RESET_STACK)


async def _handle_existing_user(
    message: Message,
    dialog_manager: DialogManager,
    backend: BackendAPIClient,
    tg_id: int,
    landing_uid: str,
) -> None:
    """Существующий юзер: mark-converted (24ч ключ не отключается) → тарифы."""
    res = await backend.mark_landing_converted(landing_uid, tg_id)
    if not res:
        await message.answer(
            "❌ Не удалось обработать ключ. Попробуйте позже или нажмите /start"
        )
        await dialog_manager.start(MainMenu.main, mode=StartMode.RESET_STACK)
        return

    if res.get("status") == "already_claimed_other":
        await message.answer(
            "⚠️ Этот ключ уже привязан к другому аккаунту."
        )
        await dialog_manager.start(MainMenu.main, mode=StartMode.RESET_STACK)
        return

    # ok=True или already=True — ключ отмечен конвертированным, 24ч продолжает работать.
    # Ведём сразу на экран тарифов: сообщение выше обещает «оформите подписку 👇»,
    # поэтому показываем тарифы (Tariff.preview), а не ЛК или экран активации триала.
    await message.answer(
        "✅ <b>Вы уже зарегистрированы.</b>\n"
        "Ваш 24-часовой ключ продолжает работать до истечения срока.\n\n"
        "Чтобы продлить доступ — оформите подписку 👇"
    )
    await dialog_manager.start(Tariff.preview, mode=StartMode.RESET_STACK)