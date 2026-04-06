from aiogram import F, Router, html
from aiogram.filters import Command
from aiogram.types import Message

from app.bot.keyboards import PROFILE_BUTTON, get_main_menu_keyboard
from app.services.habit_service import HabitService
from app.services.user_service import UserService


router = Router(name="profile")


@router.message(Command("profile"))
@router.message(F.text == PROFILE_BUTTON)
async def profile_handler(
    message: Message,
    user_service: UserService,
    habit_service: HabitService,
) -> None:
    if message.from_user is None:
        await message.answer("Не удалось определить пользователя Telegram.")
        return

    user = await user_service.get_by_telegram_id(message.from_user.id)
    if user is None:
        await message.answer("Сначала отправь /start.")
        return

    username = f"@{user.username}" if user.username else "не указан"
    created_at = user.created_at.strftime("%d.%m.%Y %H:%M")
    active_habits_count = await habit_service.count_active_habits(user.id)
    due_today_count = await habit_service.count_due_today(user.id)
    completed_today_count = await habit_service.count_completed_today(user.id)

    await message.answer(
        "\n".join(
            [
                "👤 Твой профиль",
                "",
                f"Имя в Telegram: {html.quote(username)}",
                f"В боте с: {created_at}",
                "",
                f"Активных привычек: {active_habits_count}",
                f"На сегодня запланировано: {due_today_count}",
                f"Отмечено сегодня: {completed_today_count}",
            ]
        ),
        reply_markup=get_main_menu_keyboard(
            show_admin_button=UserService.should_show_admin_entry(user)
        ),
    )
