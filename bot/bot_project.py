import traceback

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import ErrorEvent, BotCommand, BotCommandScopeDefault

from config import API_TOKEN
from logger import logger


bot = Bot(token=API_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
storage = MemoryStorage()
dp = Dispatcher(bot=bot, storage=storage)


async def set_bot_commands(bot: Bot):
    commands = [BotCommand(command="/profile", description="👤 Мой профиль")]

    await bot.set_my_commands(commands, BotCommandScopeDefault())


@dp.error()
async def error_handler(event: ErrorEvent):
    logger.error(
        "Ошибка в боте:\n"
        f"Исключение: {event.exception}\n"
        f"Тип: {type(event.exception)}\n"
        f"Update: {event.update}\n"
        f"Трассировка:\n{traceback.format_exc()}"
    )
