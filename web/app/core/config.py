import os
from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict


# Locate .env in project root (accounting for worktree: web/app/core/config.py → need 7 parents to reach /home/claude/vpn-platform/)
_env_path = Path(__file__).parent.parent.parent.parent.parent.parent.parent / ".env"
if not _env_path.exists():
    # Fallback: try worktree root (4 parents)
    _env_path = Path(__file__).parent.parent.parent.parent / ".env"
_env_file = _env_path

class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=str(_env_file), extra="ignore")

    database_url: str
    secret_key: str
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 30
    refresh_token_expire_days: int = 30
    telegram_bot_token: str
    telegram_bot_username: str = ""
    yookassa_shop_id: str
    yookassa_secret_key: str
    xui_api_url: str
    xui_subscription_url: str = ""
    xui_login: str
    xui_password: str
    xui_inbound_id: int = 1
    admin_tg_ids: list[int] = []
    login_code_ttl_hours: int = 24
    bot_secret_key: str = ""
    webhook_base_url: str
    disable_webhook_ip_check: bool = False
    csrf_enabled: bool = True

    log_level: str = "INFO"
    log_file: str = ""
    log_format: str = "detailed"

    # Bot-specific settings
    default_trial_tariff_id: int = 10  # Тариф для пробного периода (обычно с amount=0)
    default_server_id: int = 2  # Default server ID for new users
    referral_bonus_percent: float = 0.10  # 10% бонус реферера (доля от суммы платежа)
    discounts: int = 3  # 3% скидка за многомесячную подписку (2-6 месяцев)

    # Tariffs visibility
    available_rates: list[int] = []  # Тарифы для обычных пользователей (пустой список = все тарифы)

    # Backend API configuration
    backend_url: str = os.getenv("BACKEND_URL", "http://localhost:8000")
    admin_api_key: str = ""

    # Invite token for registration
    invite_token: str = "changeme"
    captcha_secret: str = "changeme_captcha"


settings = Settings()
