from dialogs.templates.instruction_step import make_instruction_window


def test_make_instruction_window():
    # Подготовка данных
    device = "Android"
    state = "Instruction.Android"
    download_url = "https://example.com/download"
    icon = "📱"

    # Вызов функции
    window = make_instruction_window(device, state, download_url, icon)

    # Проверки
    assert window["state"] == state
    assert device in window["text"]
    assert "Скачайте приложение" in window["text"]
    assert len(window["buttons"]) == 3

    download_button = window["buttons"][0]
    assert download_button["type"] == "url"
    assert download_button["url"] == download_url
    assert icon in download_button["text"]

    next_button = window["buttons"][1]
    assert next_button["type"] == "button"
    assert next_button["id"] == "next_stape"
    assert next_button["on_click"] == "getters.keys.trial_key.on_click_create_trial_key"

    back_button = window["buttons"][2]
    assert back_button["type"] == "switch_to"
    assert back_button["text"] == "Назад ↩️"
    assert back_button["state"] == "Instruction.choosing_device"
