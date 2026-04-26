import asyncpg
from punq import Container, Scope
from logger import logger
from database.base import create_db_pool
from services.conteiner.registrate.core import __all__ as core
from services.conteiner.registrate.scenario import __all__ as scenario
from services.conteiner.registrate.getters import __all__ as getters
from services.conteiner.registrate.payment import __all__ as payment


async def create_container() -> Container:
    container = Container()
    registrars = core + scenario + getters + payment

    # Регистрируем пул соединений
    pool: asyncpg.Pool = await create_db_pool()
    container.register(asyncpg.Pool, instance=pool, scope=Scope.singleton)

    # Регистрируем зависимости через экземпляры
    for registrar in registrars:
        registrar().register_dependencies(container=container)

    return container
