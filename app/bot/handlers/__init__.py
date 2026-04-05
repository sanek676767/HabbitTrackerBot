from app.bot.handlers.admin import router as admin_router
from app.bot.handlers.create_habit import router as create_habit_router
from app.bot.handlers.edit_habit import router as edit_habit_router
from app.bot.handlers.feedback import router as feedback_router
from app.bot.handlers.habits import router as habits_router
from app.bot.handlers.help import router as help_router
from app.bot.handlers.progress import router as progress_router
from app.bot.handlers.profile import router as profile_router
from app.bot.handlers.reminders import router as reminders_router
from app.bot.handlers.start import router as start_router
from app.bot.handlers.today import router as today_router

routers = (
    start_router,
    help_router,
    admin_router,
    feedback_router,
    profile_router,
    progress_router,
    create_habit_router,
    edit_habit_router,
    reminders_router,
    habits_router,
    today_router,
)

__all__ = ["routers"]
