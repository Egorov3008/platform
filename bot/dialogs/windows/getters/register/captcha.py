import random
from typing import Dict, Any

from aiogram_dialog import DialogManager

from dialogs.windows.base import DataGetter


class CaptchaGetter(DataGetter):
    """Геттер для окна капчи. Генерирует арифметический пример при первом вызове."""

    async def get_data(self, dialog_manager: DialogManager, **kwargs) -> Dict[str, Any]:
        if "captcha_answer" not in dialog_manager.dialog_data:
            a = random.randint(1, 20)
            b = random.randint(1, 20)
            dialog_manager.dialog_data["captcha_question"] = f"{a} + {b} = ?"
            dialog_manager.dialog_data["captcha_answer"] = a + b

        return {
            "captcha_question": dialog_manager.dialog_data.get("captcha_question", "? + ? = ?"),
        }
