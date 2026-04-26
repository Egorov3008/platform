# services/container/app.py
from punq import Container

_container: Container | None = None


async def get_container() -> Container:
    global _container
    if _container is None:
        from services.conteiner import create_container

        _container = await create_container()
    return _container
