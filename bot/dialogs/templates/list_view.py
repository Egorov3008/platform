# dialogs/templates/list_view.py
"""
Шаблон для окон со списком (ключи, тарифы, пользователи)
"""


def make_select_window(
    state: str,
    text: str,
    items_key: str,
    display_field: str,
    id_getter_expr: str,
    on_click: str,
    back_state: str,
    back_text: str = "Назад",
):
    """
    Создаёт окно с выбором из списка (например, тарифов или ключей).

    :param state: Состояние окна
    :param text: Основной текст
    :param items_key: Ключ в data, содержащий список элементов
    :param display_field: Как отображать элемент (например: "{item[0]}")
    :param id_getter_expr: Как получить ID (например: "index:1" или "attr:id")
    :param on_click: Функция при выборе
    :param back_state: Состояние при возврате
    :param back_text: Текст кнопки "Назад"
    :return: dict — DLS-описание окна
    """
    return {
        "state": state,
        "text": text,
        "buttons": [
            {
                "type": "select",
                "id": f"s_{items_key}",
                "text": display_field,
                "items": items_key,
                "item_id_getter": id_getter_expr,
                "on_click": on_click,
            },
            {"type": "switch_to", "text": back_text, "state": back_state},
        ],
    }
