from config import DOWNLOAD_ANDROID
from dialogs.windows.widgets.keybord.instruction.base_device import BaseDeviceKeyboard


class AndroidDeviceKeyboard(BaseDeviceKeyboard):
    _download_url = DOWNLOAD_ANDROID
    _download_label = "🤖 Скачать приложение"
    _next_btn_id = "next_android"
