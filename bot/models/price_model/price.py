from dataclasses import dataclass
from decimal import Decimal
from typing import Union

Number = Union[float, Decimal]


@dataclass
class Price:
    """
    Модель цены с поддержкой фиксированной и процентной скидки.
    """

    amount: Number = Decimal("0.0")
    stock: Number = Decimal("0.0")
    type_stock: str = ""  # "fix" or "percent"

    def __post_init__(self):
        if self.amount < 0:
            raise ValueError("amount не может быть отрицательным")
        if self.stock < 0:
            raise ValueError("stock не может быть отрицательным")
        if self.type_stock not in ("", "fix", "percent"):
            raise ValueError("type_stock должен быть 'fix', 'percent' или пустым")

    @property
    def format_price(self) -> Number:
        """
        Возвращает итоговую цену с учётом скидки.

        Поддерживает смешанные типы ``amount`` (float) и ``stock`` (Decimal) —
        всё приводится к ``Decimal`` для арифметики, чтобы избежать
        ``TypeError`` от смешения ``float`` и ``Decimal``.
        """
        amount = Decimal(str(self.amount))
        if self.stock == 0 or self.stock == Decimal("0"):
            return self.amount
        if self.type_stock == "fix":
            return max(Decimal("0"), amount - Decimal(str(self.stock)))
        if self.type_stock == "percent":
            return amount * (Decimal("1") - Decimal(str(self.stock)) / Decimal("100"))
        return self.amount

    def __repr__(self) -> str:
        return f"Price(amount={self.amount}, stock={self.stock}{f'{self.type_stock[0].upper()}' if self.type_stock else ''})"
