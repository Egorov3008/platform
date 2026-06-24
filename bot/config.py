import ast
import os
import sys
from pathlib import Path

from dotenv import load_dotenv, find_dotenv
from logger import logger

from shared.config import core_settings, REFERRAL_BONUS_PERCENTAGES  # noqa: F401

if not find_dotenv():
    logger.info("Переменные окружения не загружены т.к отсутствует файл .env")
else:
    load_dotenv()


REQUIRED_ENV = [
    "BOT_TOKEN",
    "ADMIN_ID",
    "DATABASE_URL",
    "AVAILABLE_CONNECTIONS",
    "AVAILABLE_RATES",
    "PAYMENT_INFO",
]

_missing = [var for var in REQUIRED_ENV if not os.getenv(var)]
if _missing:
    logger.critical(
        "Отсутствуют обязательные переменные окружения",
        missing_vars=_missing,
        required_vars=REQUIRED_ENV
    )
    sys.exit(1)


def _safe_literal_eval(value: str | None, var_name: str):
    """Безопасный ast.literal_eval с понятным сообщением об ошибке."""
    if value is None:
        logger.critical("Переменная окружения не задана", var_name=var_name)
        sys.exit(1)
    try:
        return ast.literal_eval(value)
    except (ValueError, SyntaxError) as e:
        logger.critical(
            "Ошибка парсинга переменной окружения",
            var_name=var_name,
            var_value=repr(value),
            error_type=type(e).__name__,
            error_message=str(e)
        )
        sys.exit(1)


API_TOKEN = os.getenv("BOT_TOKEN")

ADMIN_USERNAME = os.getenv("ADMIN_USERNAME")
ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD")
ADD_CLIENT_URL = os.getenv("ADD_CLIENT_URL")
API_URL = os.getenv("API_URL")
BACKEND_URL = os.getenv("BACKEND_URL", "http://localhost:8000")
# BOT_SECRET_KEY — sourced from .env or shared.core_settings fallback
BOT_SECRET_KEY = os.getenv("BOT_SECRET_KEY", "") or core_settings.bot_secret_key
INVITE_TOKEN = os.getenv("INVITE_TOKEN", "changeme")

DB_NAME = os.getenv("DB_NAME")
DB_PASSWORD = os.getenv("DB_PASSWORD")
LOG_DIR = os.path.abspath("logs")
DB_USER = os.getenv("DB_USER")
# DATABASE_URL — prefer .env value, fall back to shared.core_settings
DATABASE_URL = os.getenv("DATABASE_URL") or core_settings.database_url
BACK_DIR = os.path.abspath("backup")

ADMIN = os.getenv("ADMIN_ID")
ADMIN_ID = _safe_literal_eval(ADMIN, "ADMIN_ID")
CHANNEL_URL = os.getenv("CHANNEL_URL")
AVAILABLE_CONNECTIONS = os.getenv("AVAILABLE_CONNECTIONS")
DEFAULT_PRICING_PLAN = os.getenv("DEFAULT_PRICING_PLAN")
AVAILABLE_RATES = os.getenv("AVAILABLE_RATES")
AVAILABLE_RATES_LIST = _safe_literal_eval(AVAILABLE_RATES, "AVAILABLE_RATES")

DEV_MODE = False
# YooKassa — sourced from .env, with shared.core_settings fallback
YOOKASSA_SECRET_KEY = (
    os.getenv("YOOKASSA_SECRET_KEY") or core_settings.yookassa_secret_key
)
YOOKASSA_SHOP_ID = (
    os.getenv("YOOKASSA_SHOP_ID") or core_settings.yookassa_shop_id
)
CRYPTO_BOT_ENABLE = False
FREEKASSA_ENABLE = False
LEGACY_ENABLE = False
ROBOKASSA_ENABLE = False
SUB_PATH = None
YOOKASSA_ENABLE = False
# REFERRAL_BONUS_PERCENTAGES — single source of truth in shared.config
URL_BOT = os.getenv("URL_BOT")
PAYMENT_INFO = os.getenv("PAYMENT_INFO")
payment_info_dict = _safe_literal_eval(PAYMENT_INFO, "PAYMENT_INFO")
TECHNICAL_SUPPORT = os.getenv("TECHNICAL_SUPPORT")
LIST_AVAILABLE_CONNECTIONS = _safe_literal_eval(
    AVAILABLE_CONNECTIONS, "AVAILABLE_CONNECTIONS"
)
LIMIT_IP = 3
PUBLIC_LINK = "https://text-3x.duckdns.org:2096/OnyTolkoPodpis4iki/"
BOT_NAME = os.getenv("BOT_NAME")
WEBHOOK_HOST = os.getenv("WEBHOOK_HOST")
WEBHOOK_PORT = os.getenv("WEBHOOK_PORT")
WEBHOOK_URL = os.getenv("WEBHOOK_URL")
WEBHOOK_PATH = os.getenv("WEBHOOK_PATH")
DISABLE_WEBHOOK_IP_CHECK = os.getenv("DISABLE_WEBHOOK_IP_CHECK", "false").lower() == "true"
SUPPORT_CHAT_URL = os.getenv("SUPPORT_CHAT_URL")
WEBAPP_HOST = os.getenv("WEBAPP_HOST")
WEBAPP_PORT = os.getenv("WEBAPP_PORT")
# METRICS_PORT — shared.core_settings is the canonical default
METRICS_PORT = int(os.getenv("METRICS_PORT", str(core_settings.metrics_port)))
BACKUP_TIME = 86400
BASE_DIR = Path(__file__).parent
VIDEOS_DIR = BASE_DIR / "video_instructions"
SUBSTACTION_URL = "https://host-vps.duckdns.org:2096/TolkoDlyaSv0ih_Bot"
CONNECT_ANDROID = (
    "https://play.google.com/store/apps/details?id=com.happproxy&hl=ru"
)
DOWNLOAD_IOS = "https://apps.apple.com/us/app/happ-proxy-utility/id6504287215"
DOWNLOAD_ANDROID = (
    "https://play.google.com/store/apps/details?id=com.happproxy&hl=ru"
)
DOWNLOAD_WIN = "https://github.com/Happ-proxy/happ-desktop/releases/latest/download/setup-Happ.x64.exe"
DOWNLOAD_LIN = "https://github.com/Happ-proxy/happ-desktop/releases/latest/download/Happ.linux.x64.deb"

RENEWAL_PRICES = {"1": 1}
CONNECT_WINDOWS = "https://github.com/Happ-proxy/happ-desktop/releases/latest/download/setup-Happ.x64.exe"
# TRIAL_TIME — shared.core_settings is the canonical default
TRIAL_TIME = int(os.getenv("TRIAL_TIME", str(core_settings.trial_time)))

SERVERS = {"1": {}}
NEWS_MESSAGE = "У нас нет новостей 🙊"

DEFAULT_COMMANDS = (
    ("start", "Запустить бота"),
    ("help", "Список команд"),
)
PROJECT_NAME = "MyVPNService"
SUB_MESSAGE = "Ваш надежный сервис для безопасного серфинга."
DICTIONARY_OF_DISCOUNTS = {}

# DISCOUNTS — sourced from .env, with shared.core_settings fallback
DISCOUNTS: int = int(os.getenv("DISCOUNTS", str(core_settings.discounts)))
