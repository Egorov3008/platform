__all__ = ("router",)

from aiogram import Router

from .start import router as start_router
from .admin import router as admin_router
from .notifications import router as notifications_router

router: Router = Router(name="handlers_main_router")

router.include_routers(
    start_router,
    admin_router,
    notifications_router,
)
