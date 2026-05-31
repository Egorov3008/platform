"""Stub: business cache loading removed. Bot fetches all data from backend API."""

from logger import logger


class LoadingService:
    """No-op loader: bot no longer maintains a business cache."""

    def __init__(self, *args, **kwargs):
        pass

    async def loading(self):
        logger.info("Business cache loading skipped (bot uses backend API)")

    async def load_server(self):
        logger.info("Server cache loading skipped (bot uses backend API)")
