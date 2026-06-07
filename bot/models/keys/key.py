import dataclasses
from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from typing import Optional, Dict, Any, Union

try:
    from pydantic import BaseModel
    HAS_PYDANTIC = True
except ImportError:
    HAS_PYDANTIC = False


def default_created_at():
    return int(datetime.now().timestamp() * 1000)


@dataclass
class Key:
    tg_id: int
    client_id: str
    email: str
    expiry_time: int
    key: str
    inbound_id: int
    tariff_id: Optional[int] = None
    total_gb: Optional[int] = 10
    created_at: int = None
    reset_date: int = 0
    notified_10h: bool = False
    notified_24h: bool = False
    tariff_description: Optional[str] = None
    name_tariff: Optional[str] = None
    amount: Optional[float] = None
    limit_ip: Optional[int] = None
    period: Optional[int] = None
    used_traffic: Optional[float] = 0
    server_info: Optional[Any] = None
    _name: str = "key"

    def __post_init__(self):
        if self.created_at is None:
            self.created_at = default_created_at()

    _DB_FIELDS = frozenset(
        {
            "tg_id",
            "client_id",
            "email",
            "created_at",
            "expiry_time",
            "key",
            "total_gb",
            "reset_date",
            "inbound_id",
            "notified_10h",
            "notified_24h",
            "tariff_id",
        }
    )

    def to_dict(self) -> Dict[str, Any]:
        return {k: v for k, v in asdict(self).items() if k in self._DB_FIELDS}

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Key":
        return cls(**data)

    @classmethod
    def from_backend(cls, data: Union[Dict[str, Any], Any]) -> "Key":
        """Build a Key model from backend API response dict, dataclass, or pydantic DTO."""
        if isinstance(data, dict):
            d = data
        elif dataclasses.is_dataclass(data) and not isinstance(data, type):
            d = dataclasses.asdict(data)
        elif HAS_PYDANTIC and isinstance(data, BaseModel):
            d = data.model_dump()
        else:
            d = getattr(data, "__dict__", {})
        return cls(
            tg_id=d.get("tg_id"),
            client_id=d.get("client_id", ""),
            email=d.get("email"),
            expiry_time=d.get("expiry_time"),
            key=d.get("key"),
            inbound_id=d.get("inbound_id"),
            tariff_id=d.get("tariff_id"),
            total_gb=d.get("total_gb", 10),
            name_tariff=d.get("name_tariff"),
            used_traffic=d.get("used_traffic", 0.0),
            limit_ip=d.get("limit_ip"),
            period=d.get("period"),
            notified_10h=d.get("notified_10h", False),
            notified_24h=d.get("notified_24h", False),
        )

    @property
    def name(self) -> str:
        return self._name

    @property
    def warp_expiry_time(self) -> str:
        """Возвращает время истечения ключа в формате 'ГГГГ-ММ-ДД ЧЧ:ММ'."""
        expiry_timestamp = self.expiry_time / 1000  # мс → сек
        dt = datetime.fromtimestamp(expiry_timestamp, tz=timezone.utc)
        return dt.strftime("%Y-%m-%d %H:%M")
