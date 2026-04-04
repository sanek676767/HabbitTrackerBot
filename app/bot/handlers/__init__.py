from app.bot.handlers.menu import router as menu_router
from app.bot.handlers.profile import router as profile_router
from app.bot.handlers.start import router as start_router

routers = (start_router, profile_router, menu_router)

__all__ = ["routers"]
