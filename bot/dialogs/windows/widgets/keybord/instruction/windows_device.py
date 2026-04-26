from config import DOWNLOAD_WIN
from dialogs.windows.widgets.keybord.instruction.base_device import BaseDeviceKeyboard


class WindowsDeviceKeyboard(BaseDeviceKeyboard):
    _download_url = DOWNLOAD_WIN
    _download_label = "🪟 Скачать приложение"
    _next_btn_id = "next_windows"
