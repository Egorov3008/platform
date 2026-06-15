from dataclasses import dataclass, asdict, is_dataclass
from datetime import datetime
from typing import Optional, Dict, Any, Union

try:
    from pydantic import BaseModel
    HAS_PYDANTIC = True
except ImportError:
    HAS_PYDANTIC = False


def default_created_at():
    return datetime.now()


def default_updated_at():
    return datetime.now()


@dataclass
class User:
    tg_id: int
    created_at: datetime = None
    username: Optional[str] = None
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    language_code: Optional[str] = None
    is_bot: bool = False
    updated_at: datetime = None
    is_admin: bool = False
    balance: float = 0.0
    trial: int = 0
    server_id: Optional[int] = None
    referral_id: Optional[int] = None
    check_referral: bool = False
    is_blocked: bool = False
    _name = "user"

    def __post_init__(self):
        if self.created_at is None:
            self.created_at = default_created_at()
        if self.updated_at is None:
            self.updated_at = default_updated_at()

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "User":
        """Создает экземпляр User из словаря."""
        return cls(**data)

    @classmethod
    def from_backend(cls, data: Union[Dict[str, Any], Any]) -> "User":
        """Build a User model from backend API response (dict, dataclass, or pydantic DTO).

        Mirrors ``Key.from_backend``. Extracts only the fields that the backend
        ``UserResponse`` schema actually returns — see
        ``backend/app/schemas/users.py``. Unknown fields are ignored; missing
        fields fall back to dataclass defaults.
        """
        if isinstance(data, dict):
            d = data
        elif is_dataclass(data) and not isinstance(data, type):
            d = asdict(data)
        elif HAS_PYDANTIC and isinstance(data, BaseModel):
            d = data.model_dump()
        else:
            d = getattr(data, "__dict__", {})

        return cls(
            tg_id=d.get("tg_id"),
            username=d.get("username"),
            first_name=d.get("first_name"),
            last_name=d.get("last_name"),
            language_code=d.get("language_code"),
            is_admin=d.get("is_admin", False),
            balance=d.get("balance", 0.0),
            trial=d.get("trial", 0),
            server_id=d.get("server_id"),
            referral_id=d.get("referral_id"),
            is_blocked=d.get("is_blocked", False),
        )

    @property
    def name(self) -> str:
        return self._name
