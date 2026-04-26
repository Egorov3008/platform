from jinja2 import Environment


from dialogs.messages.users.tariff import TARIFF_TEMPLATE


def test_tariff_template_is_string():
    assert isinstance(TARIFF_TEMPLATE, str)
    assert len(TARIFF_TEMPLATE) > 0


def test_tariff_template_content():
    assert "🚀 ДОСТУПНЫЕ ТАРИФЫ" in TARIFF_TEMPLATE
    assert "{{ discount }}" in TARIFF_TEMPLATE
    assert "{{ tariff.name_tariff }}" in TARIFF_TEMPLATE
    assert "{{ tariff.description }}" in TARIFF_TEMPLATE
    assert "{{ tariff.amount }}" in TARIFF_TEMPLATE


def test_tariff_template_conditionals():
    assert "{% if discount > 0 %}" in TARIFF_TEMPLATE
    assert "{% endif %}" in TARIFF_TEMPLATE
    assert "{% for tariff in tariffs %}" in TARIFF_TEMPLATE
    assert "{% endfor %}" in TARIFF_TEMPLATE


def test_tariff_template_rounding():
    assert "round(0, 'floor')" in TARIFF_TEMPLATE
    assert "| int" in TARIFF_TEMPLATE


def test_tariff_template_with_discount_render():
    env = Environment(autoescape=False)
    template = env.from_string(TARIFF_TEMPLATE)

    data = {
        "discount": 20,
        "tariffs": [
            {"name_tariff": "Стандарт", "description": "Базовый тариф", "amount": 500},
            {
                "name_tariff": "Премиум",
                "description": "Максимальная скорость",
                "amount": 800,
            },
        ],
    }

    rendered = template.render(data)

    assert "ВАМ ПРЕДОСТАВЛЕНА СКИДКА 20%" in rendered
    assert "<s>500₽</s>" in rendered
    assert "400₽" in rendered  # 500 * 0.8
    assert "<s>800₽</s>" in rendered
    assert "640₽" in rendered  # 800 * 0.8


def test_tariff_template_without_discount_render():
    env = Environment(autoescape=False)
    template = env.from_string(TARIFF_TEMPLATE)

    data = {
        "discount": 0,
        "tariffs": [
            {"name_tariff": "Стандарт", "description": "Базовый тариф", "amount": 500},
        ],
    }

    rendered = template.render(**data)

    assert "ВАМ ПРЕДОСТАВЛЕНА СКИДКА" not in rendered
    assert "<s>" not in rendered
    assert "500₽" in rendered


def test_tariff_template_empty_tariffs():
    env = Environment(autoescape=False)
    template = env.from_string(TARIFF_TEMPLATE)

    data = {"discount": 10, "tariffs": []}
    rendered = template.render(**data)

    assert "🚀 ДОСТУПНЫЕ ТАРИФЫ" in rendered
    assert "name_tariff" not in rendered


def test_tariff_template_special_characters():
    env = Environment(autoescape=False)
    template = env.from_string(TARIFF_TEMPLATE)

    data = {
        "discount": 15,
        "tariffs": [
            {
                "name_tariff": "Тариф & Специальные <b>теги</b>",
                "description": "Описание с & символами",
                "amount": 1000,
            }
        ],
    }

    rendered = template.render(**data)

    assert "Тариф & Специальные <b>теги</b>" in rendered
