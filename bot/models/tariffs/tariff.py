import dataclasses
from dataclasses import dataclass, asdict
from typing import Optional, Dict, Any, ClassVar, Mapping


@dataclass
class Tariff:
    id: int
    name_tariff: str
    amount: float = 0.0
    description: Optional[str] = None
    limit_ip: int = 0
    period: int = 30
    traffic_limit: int = 0
    is_active: bool = True
    _name: ClassVar[str] = "tariff"

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> "Tariff":
        # Принимаем как dict, так и Pydantic-модель (TariffDTO).
        # После Stage 4 BackendAPIClient.get_tariff() возвращает TariffDTO,
        # и cls(**TariffDTO) падал с TypeError "must be a mapping".
        if isinstance(data, Mapping):
            payload: Dict[str, Any] = dict(data)
        elif hasattr(data, "model_dump"):  # Pydantic v2
            payload = data.model_dump()
        elif hasattr(data, "dict"):  # Pydantic v1
            payload = data.dict()
        else:
            raise TypeError(
                f"Tariff.from_dict expects a mapping or Pydantic model, got {type(data).__name__}"
            )
        # Отбрасываем поля, которых нет в dataclass (например, DTO может
        # расширяться в будущем, а старый UI-слой не должен ломаться).
        allowed = {f.name for f in dataclasses.fields(cls)}
        payload = {k: v for k, v in payload.items() if k in allowed}
        return cls(**payload)

    @property
    def name(self) -> str:
        return self._name
