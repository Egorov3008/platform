from dialogs.templates.list_view import make_select_window


def test_make_select_window():
    # Подготовка данных
    state = "TariffSelection"
    text = "Выберите тариф:"
    items_key = "tariffs"
    display_field = "{item[0]} - {item[1]} руб/мес"
    id_getter_expr = "index:1"
    on_click = "handlers.tariffs.on_tariff_selected"
    back_state = "MainMenu"

    # Вызов функции
    window = make_select_window(
        state, text, items_key, display_field, id_getter_expr, on_click, back_state
    )

    # Проверки
    assert window["state"] == state
    assert window["text"] == text
    assert len(window["buttons"]) == 2

    select_button = window["buttons"][0]
    assert select_button["type"] == "select"
    assert select_button["id"] == f"s_{items_key}"
    assert select_button["text"] == display_field
    assert select_button["items"] == items_key
    assert select_button["item_id_getter"] == id_getter_expr
    assert select_button["on_click"] == on_click

    back_button = window["buttons"][1]
    assert back_button["type"] == "switch_to"
    assert back_button["text"] == "Назад"
    assert back_button["state"] == back_state
