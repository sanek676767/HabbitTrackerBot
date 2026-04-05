from aiogram import F, Router
from aiogram.types import CallbackQuery, InlineKeyboardMarkup, Message

from app.bot.callbacks import HabitListSource, OpenTodayCallback
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
        await message.answer("Сначала отправь /start.")
        return

    text, reply_markup = await _build_today_screen_text(user.id, habit_service)
    await message.answer(text, reply_markup=reply_markup)


@router.callback_query(OpenTodayCallback.filter())
async def open_today_from_callback(
    callback: CallbackQuery,
    user_service: UserService,
    habit_service: HabitService,
) -> None:
    if callback.from_user is None or callback.message is None:
        await callback.answer()
        return

    user = await user_service.get_by_telegram_id(callback.from_user.id)
    if user is None:
        await callback.answer("Сначала отправь /start.", show_alert=True)
        return

    text, reply_markup = await _build_today_screen_text(user.id, habit_service)
    await callback.message.edit_text(text, reply_markup=reply_markup)
    await callback.answer()


async def _build_today_screen_text(
    user_id: int,
    habit_service: HabitService,
) -> tuple[str, InlineKeyboardMarkup | None]:
    habits = await habit_service.get_today_habits(user_id)
    if not habits:
        return ("Сегодня по расписанию привычек нет.", None)

    return (
        "🔥 Сегодня\n\nЗдесь только те привычки, которые запланированы на сегодня.",
        get_habits_list_keyboard(
            habits,
            HabitListSource.TODAY.value,
            show_completion_status=True,
        ),
    )
