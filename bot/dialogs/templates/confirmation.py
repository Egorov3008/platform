# dialogs/templates/confirmation.py
"""
Шаблон для окон подтверждения (удаление, оплата, изменение и т.д.)
"""


def make_confirmation_window(
    state: str,
    text: str,
    confirm_id: str,
    confirm_text: str,
    confirm_click: str,
    back_state: str,
    back_text: str = "Назад",
):
    """
    Универсальный шаблон подтверждения действия.

    :param state: Состояние окна
    :param text: Текст подтверждения (может содержать {variables})
    :param confirm_id: ID кнопки подтверждения
    :param confirm_text: Текст кнопки "Да"
    :param confirm_click: Функция on_click при подтверждении
    :param back_state: Состояние при отмене
    :param back_text: Текст кнопки "Назад"
    :return: dict — DLS-описание окна
    """
    return {
        "state": state,
        "text": text,
        "buttons": [
            {
                "type": "button",
                "text": confirm_text,
                "id": confirm_id,
                "on_click": confirm_click,
            },
            {"type": "switch_to", "text": back_text, "state": back_state},
        ],
    }
