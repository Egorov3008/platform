# dialogs/loader.py
"""
Автоматическая загрузка всех диалогов из dialogs/flows/*.yaml
"""

from pathlib import Path
from typing import List
from aiogram_dialog import Dialog

from .dialog_factory import WindowFactory

DIALOGS_DIR = Path(__file__).parent / "flows"


def load_all_dialogs() -> List[Dialog]:
    """
    Загружает все DLS-файлы из папки `flows` и возвращает список Dialog.
    Игнорирует файлы с префиксом `_` или `.`.
    """
    dialogs = []
    yaml_files = sorted(DIALOGS_DIR.glob("*.yaml"))

    for file_path in yaml_files:
        if file_path.name.startswith(("_", ".")):
            continue

        print(f"[Dialog Loader] Загрузка: {file_path.name}")
        try:
            windows = WindowFactory.from_yaml_file(str(file_path))
            dialog = Dialog(*windows)
            dialogs.append(dialog)
            print(
                f"[Dialog Loader] Успешно загружено: {file_path.stem} ({len(windows)} окон)"
            )
        except Exception as e:
            print(f"[Dialog Loader] Ошибка при загрузке {file_path.name}: {e}")
            raise

    return dialogs
