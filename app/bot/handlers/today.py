from aiogram import F, Router
from aiogram.types import Message

from app.bot.callbacks import HabitListSource
from app.bot.keyboards import TODAY_BUTTON, get_habits_list_keyboard
from app.services.habit_service import HabitService
from app.services.user_service import UserService


router = Router(name="today")


@router.message(F.text == TODAY_BUTTON)
async def show_today_habits(
    message: Message,
    user_service: UserService,
    habit_service: HabitService,
) -> None:
    if message.from_user is None:
        await message.answer("Не удалось определить пользователя Telegram.")
        return

    user = await user_service.get_by_telegram_id(message.from_user.id)
    if user is None:
        await message.answer("Сначала отправьте /start.")
        return

    habits = await habit_service.get_today_habits(user.id)
    if not habits:
        await message.answer("У тебя пока нет активных привычек на сегодня.")
        return

    await message.answer(
        "Сегодня:\nВыбери привычку, чтобы открыть карточку.",
        reply_markup=get_habits_list_keyboard(
            habits,
            HabitListSource.TODAY.value,
            show_completion_status=True,
        ),
    )
