# dialogs/templates/instruction_step.py
"""
Шаблон для окон инструкций (Android, iPhone, Windows и т.д.)
"""


def make_instruction_window(device: str, state: str, download_url: str, icon: str):
    """
    Создаёт окно с кнопкой скачивания и переходом к следующему шагу.

    :param device: Название устройства (для текста)
    :param state: Состояние окна
    :param download_url: URL для скачивания
    :param icon: Иконка устройства
    :return: dict — DLS-описание окна
    """
    return {
        "state": state,
        "text": f"Скачайте приложение для {device}.\nПосле чего перейдите к следующему шагу 👇",
        "buttons": [
            {"type": "url", "text": f"{icon} Скачать приложение", "url": download_url},
            {
                "type": "button",
                "text": "Следующий шаг ▶️",
                "id": "next_stape",
                "on_click": "getters.keys.trial_key.on_click_create_trial_key",
            },
            {
                "type": "switch_to",
                "text": "Назад ↩️",
                "state": "Instruction.choosing_device",
            },
        ],
    }
