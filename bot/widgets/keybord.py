from aiogram_dialog.widgets.text import Jinja
from aiogram_dialog.widgets.kbd import Select

from getters.on_click.key_click import on_click_view_key_admin


def key_selector() -> Select:
    return Select(
        Jinja(
            "{{ item.email }} "
            "10H {{ '🟢' if item.notified_10h else '🔴' }} "
            "24h {{ '🟢' if item.notified_24h else '🔴' }}"
        ),
        id="s_keys",
        item_id_getter=lambda key: key.email,  # Используем email как ID
        items="keys",  # Берем из данных, возвращаемых геттером
        # Обработчик нажатия на ключ (можно перейти к деталям)
        on_click=on_click_view_key_admin,
    )
