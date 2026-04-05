from aiogram import F, Router, html
from aiogram.types import CallbackQuery, Message

from app.bot.callbacks import OpenProgressCallback
from app.bot.keyboards import PROGRESS_BUTTON, get_progress_screen_keyboard
from app.services.progress_service import ProgressScreenData, ProgressService
from app.services.user_service import UserService


router = Router(name="progress")


@router.message(F.text == PROGRESS_BUTTON)
async def show_progress_screen(
    message: Message,
    user_service: UserService,
    progress_service: ProgressService,
) -> None:
    if message.from_user is None:
        await message.answer("Не удалось определить пользователя Telegram.")
        return

    user = await user_service.get_by_telegram_id(message.from_user.id)
    if user is None:
        await message.answer("Сначала отправь /start.")
        return

    progress_data = await progress_service.get_progress_screen_data(user.id)
    await message.answer(
        _build_progress_screen_text(progress_data),
        reply_markup=get_progress_screen_keyboard(),
    )


@router.callback_query(OpenProgressCallback.filter())
async def open_progress_from_callback(
    callback: CallbackQuery,
    user_service: UserService,
    progress_service: ProgressService,
) -> None:
    if callback.from_user is None or callback.message is None:
        await callback.answer()
        return

    user = await user_service.get_by_telegram_id(callback.from_user.id)
    if user is None:
        await callback.answer("Сначала отправь /start.", show_alert=True)
        return

    progress_data = await progress_service.get_progress_screen_data(user.id)
    await callback.message.edit_text(
        _build_progress_screen_text(progress_data),
        reply_markup=get_progress_screen_keyboard(),
    )
    await callback.answer()


def _build_progress_screen_text(progress_data: ProgressScreenData) -> str:
    best_current_streak_text = (
        f"{html.quote(progress_data.best_current_streak_habit_title)} - "
        f"{progress_data.best_current_streak_value} дн."
        if progress_data.best_current_streak_habit_title is not None
        and progress_data.best_current_streak_value > 0
        else "Пока нет активной серии"
    )
    last_completed_text = (
        f"{html.quote(progress_data.last_completed_habit_title)} - "
        f"{progress_data.last_completed_at.strftime('%d.%m.%Y %H:%M')}"
        if progress_data.last_completed_habit_title is not None
        and progress_data.last_completed_at is not None
        else "Пока нет выполнений"
    )
    return "\n".join(
        [
            "📈 Прогресс",
            "",
            f"Активных привычек: {progress_data.active_habits_count}",
            f"Запланировано на сегодня: {progress_data.due_today_count}",
            f"Отмечено сегодня: {progress_data.completed_today_count}",
            f"Осталось на сегодня: {progress_data.remaining_today_count}",
            f"Процент выполнения за 7 дней: {_format_percentage(progress_data.completion_rate_7_days)}",
            f"Процент выполнения за 30 дней: {_format_percentage(progress_data.completion_rate_30_days)}",
            f"Лучшая текущая серия: {best_current_streak_text}",
            f"Последнее выполнение: {last_completed_text}",
        ]
    )


def _format_percentage(value: float) -> str:
    if value.is_integer():
        return f"{int(value)}%"
    return f"{value:.1f}%"
