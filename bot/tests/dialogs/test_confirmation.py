from dialogs.templates.confirmation import make_confirmation_window


def test_make_confirmation_window():
    # Подготовка данных
    state = "ConfirmDeleteKey"
    text = "Вы уверены, что хотите удалить ключ {key_id}?"
    confirm_id = "confirm_delete"
    confirm_text = "Да, удалить"
    confirm_click = "handlers.keys.on_delete_confirmed"
    back_state = "KeyManager"

    # Вызов функции
    window = make_confirmation_window(
        state, text, confirm_id, confirm_text, confirm_click, back_state
    )

    # Проверки
    assert window["state"] == state
    assert window["text"] == text
    assert len(window["buttons"]) == 2

    confirm_button = window["buttons"][0]
    assert confirm_button["type"] == "button"
    assert confirm_button["text"] == confirm_text
    assert confirm_button["id"] == confirm_id
    assert confirm_button["on_click"] == confirm_click

    back_button = window["buttons"][1]
    assert back_button["type"] == "switch_to"
    assert back_button["text"] == "Назад"
    assert back_button["state"] == back_state
