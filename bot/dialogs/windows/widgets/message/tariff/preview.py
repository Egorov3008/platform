from aiogram_dialog.widgets.text import Jinja

from dialogs.windows.base import MessageBuilder


class TariffPreviewMessage(MessageBuilder):
    def build(self):
        return Jinja("""✨ <b>🚀 ДОСТУПНЫЕ ТАРИФЫ</b> ✨

{% if discount_value > 0 %}
    {% if discount_type == "percent" %}
        🎁 <b>ВАМ ПРЕДОСТАВЛЕНА СКИДКА {{ discount_value }}%</b>
    {% elif discount_type == "fix" %}
        🎁 <b>ВАМ ПРЕДОСТАВЛЕНА СКИДКА {{ discount_value }}₽</b>
    {% endif %}
{% endif %}

{% for tariff_data in tariffs.values() %}
➖➖➖➖➖➖➖➖➖➖
🏷️ <b>{{ tariff_data.tariff.name_tariff }}</b>
📦 Включает: {{ tariff_data.tariff.description }}
💵 Стоимость:
    {% if discount_value > 0 %}
        <s>{{ tariff_data.tariff.amount }}₽</s>
        <b>{{ tariff_data.discounted_amount | int }}₽</b>
    {% else %}
        <b>{{ tariff_data.tariff.amount | int }}₽</b>
    {% endif %}
{% endfor %}

➖➖➖➖➖➖➖➖➖➖
""")
