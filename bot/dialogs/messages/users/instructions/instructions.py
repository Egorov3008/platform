"""
Тексты, связанные с инструкциями по использованию ключей и подключению.
Jinja-совместимые шаблоны.
"""

from config import (
    DOWNLOAD_ANDROID,
    DOWNLOAD_IOS,
    DOWNLOAD_LIN,
    DOWNLOAD_WIN,
)

INSTRUCTIONS = """📋  <b>Быстрая инструкция по подключению:</b>
1. <b>🔑  Скопируйте ключ </b>

👇👇👇👇👇👇👇👇
{{ public_link }}
☝☝☝☝☝☝☝☝☝☝

2. <b>📲  Откройте приложение и нажмите на плюсик сверху справа.</b>
3. <b>📋  Выберите 'Вставить из буфера обмена' для добавления ключа.</b>

💬  Если у вас возникнут вопросы, не стесняйтесь обращаться в поддержку.
"""

INSTRUCTION_PC = """🖥️ <b>Инструкция по подключению ПК:</b>

1. 📥 <b>Скачайте приложение Happ:</b>
   • Для Windows: <a href="{win}">Happ (скачать)</a>
   • Для macOS: <a href="{ios}">Happ из Mac App Store</a>

2. 🔧 <b>Установите приложение и запустите его.</b>
3. 🤖 <b>Вернитесь в бота и нажмите кнопку ниже для подключения 👇</b>
   🔗 Или вставьте ссылку вручную: скопируйте, нажмите + и выберите «Вставить из буфера».
""".format(win=DOWNLOAD_WIN, ios=DOWNLOAD_IOS)

ANDROID_INSTRUCTION = """📱 <b>Инструкция для Android:</b>

1. Скачайте приложение Happ:
   • <a href="{android}">Happ из Google Play</a>
   • Или <a href="https://github.com/Happ-proxy/happ-android/releases/latest/download/Happ.apk">Happ (APK)</a>

2. Установите и откройте.
3. Перейдите к следующему шагу в боте 👇
""".format(android=DOWNLOAD_ANDROID)

IPHONE_INSTRUCTION = """🍏 <b>Инструкция для iPhone:</b>

1. Скачайте приложение Happ:
   • <a href="{ios}">Happ из App Store</a>

2. Установите и запустите.
3. Вернитесь в бот и нажмите «Далее» 👇
""".format(ios=DOWNLOAD_IOS)

WINDOWS_INSTRUCTION = """💻 <b>Инструкция для Windows:</b>

1. Скачайте:
   • <a href="{win}">Happ (установщик)</a>

2. Установите, запустите приложение.
3. Нажмите «Подключиться» в боте 👇
""".format(win=DOWNLOAD_WIN)

LINUX_INSTRUCTION = """🐧 <b>Инструкция для Linux:</b>

1. Скачайте Happ:
   • <a href="{lin}">Happ (.deb, x64)</a>
   • Или <a href="https://github.com/Happ-proxy/happ-desktop/releases">остальные сборки (rpm, Arch, ARM64)</a>

2. Установите по инструкции для вашего дистрибутива.
3. Добавьте ключ вручную или через бота 👇
""".format(lin=DOWNLOAD_LIN)