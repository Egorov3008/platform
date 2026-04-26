from config import DOWNLOAD_IOS
from dialogs.windows.widgets.keybord.instruction.base_device import BaseDeviceKeyboard


class IphoneDeviceKeyboard(BaseDeviceKeyboard):
    _download_url = DOWNLOAD_IOS
    _download_label = "🍎 Скачать приложение"
    _next_btn_id = "next_iphone"
