from punq import Container
from logger import logger
from services.conteiner.registrate.core import __all__ as core
from services.conteiner.registrate.scenario import __all__ as scenario
from services.conteiner.registrate.getters import __all__ as getters


async def create_container() -> Container:
    container = Container()
    registrars = core + scenario + getters

    for registrar in registrars:
        registrar().register_dependencies(container=container)

    logger.info("DI container created")
    return container
