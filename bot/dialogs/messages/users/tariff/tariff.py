TARIFF_TEMPLATE = """
✨ <b>🚀 ДОСТУПНЫЕ ТАРИФЫ</b> ✨

{% if discount > 0 %}
🎁 <b>ВАМ ПРЕДОСТАВЛЕНА СКИДКА {{ discount }}%</b>
{% endif %}

{% for tariff in tariffs %}
➖➖➖➖➖➖➖➖➖➖
🏷️ <b>{{ tariff.name_tariff }}</b>
📦 Включает: {{ tariff.description }}
💵 Стоимость: 
    {% if discount > 0 %}
        <s>{{ tariff.amount }}₽</s> <b>{{ (tariff.amount * (1 - discount / 100)) | round(0, 'floor') | int }}₽</b>
    {% else %}
        <b>{{ tariff.amount }}₽</b>
    {% endif %}
{% endfor %}

➖➖➖➖➖➖➖➖➖➖
"""
