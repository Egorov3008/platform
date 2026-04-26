from config import DOWNLOAD_LIN
from dialogs.windows.widgets.keybord.instruction.base_device import BaseDeviceKeyboard


class LinuxDeviceKeyboard(BaseDeviceKeyboard):
    _download_url = DOWNLOAD_LIN
    _download_label = "🐧 Скачать приложение"
    _next_btn_id = "next_linux"
