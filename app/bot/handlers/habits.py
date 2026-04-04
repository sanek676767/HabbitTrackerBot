from aiogram import F, Router, html
from aiogram.types import CallbackQuery, InlineKeyboardMarkup, Message

from app.bot.callbacks import (
    HabitArchiveCallback,
    HabitDeleteCallback,
    HabitDoneCallback,
    HabitListCallback,
    HabitListSource,
    HabitRestoreCallback,
    HabitStatsCallback,
    HabitViewCallback,
)
from app.bot.keyboards import (
    MY_HABITS_BUTTON,
    get_habit_card_keyboard,
    get_habit_stats_keyboard,
    get_habits_list_keyboard,
)
from app.services.habit_service import (
    HabitAlreadyCompletedError,
    HabitArchivedError,
    HabitCard,
    HabitDeletedError,
    HabitNotFoundError,
    HabitService,
    HabitStats,
)
from app.services.user_service import UserService


router = Router(name="habits")


@router.message(F.text == MY_HABITS_BUTTON)
async def show_my_habits(
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

    text, reply_markup = await _build_active_screen(user.id, habit_service)
    await message.answer(text, reply_markup=reply_markup)


@router.callback_query(HabitListCallback.filter())
async def reopen_habit_list(
    callback: CallbackQuery,
    callback_data: HabitListCallback,
    user_service: UserService,
    habit_service: HabitService,
) -> None:
    if callback.from_user is None or callback.message is None:
        await callback.answer()
        return

    user = await user_service.get_by_telegram_id(callback.from_user.id)
    if user is None:
        await callback.answer("Сначала отправьте /start.", show_alert=True)
        return

    if callback_data.source == HabitListSource.TODAY.value:
        text, reply_markup = await _build_today_screen(user.id, habit_service)
    elif callback_data.source == HabitListSource.ARCHIVE.value:
        text, reply_markup = await _build_archive_screen(user.id, habit_service)
    else:
        text, reply_markup = await _build_active_screen(user.id, habit_service)

    await callback.message.edit_text(text, reply_markup=reply_markup)
    await callback.answer()


@router.callback_query(HabitViewCallback.filter())
async def show_habit_card(
    callback: CallbackQuery,
    callback_data: HabitViewCallback,
    user_service: UserService,
    habit_service: HabitService,
) -> None:
    if callback.from_user is None or callback.message is None:
        await callback.answer()
        return

    user = await user_service.get_by_telegram_id(callback.from_user.id)
    if user is None:
        await callback.answer("Сначала отправьте /start.", show_alert=True)
        return

    try:
        habit_card = await habit_service.get_habit_card(user.id, callback_data.habit_id)
    except HabitNotFoundError:
        await callback.answer("Привычка не найдена.", show_alert=True)
        return
    except HabitDeletedError as error:
        await callback.answer(str(error), show_alert=True)
        return

    await callback.message.edit_text(
        _build_habit_card_text(habit_card),
        reply_markup=get_habit_card_keyboard(
            habit_card.id,
            callback_data.source,
            is_completed_today=habit_card.is_completed_today,
            is_active=habit_card.is_active,
        ),
    )
    await callback.answer()


@router.callback_query(HabitDoneCallback.filter())
async def complete_habit(
    callback: CallbackQuery,
    callback_data: HabitDoneCallback,
    user_service: UserService,
    habit_service: HabitService,
) -> None:
    if callback.from_user is None or callback.message is None:
        await callback.answer()
        return

    user = await user_service.get_by_telegram_id(callback.from_user.id)
    if user is None:
        await callback.answer("Сначала отправьте /start.", show_alert=True)
        return

    try:
        habit_card = await habit_service.complete_habit_for_today(user.id, callback_data.habit_id)
    except HabitNotFoundError:
        await callback.answer("Привычка не найдена.", show_alert=True)
        return
    except HabitDeletedError as error:
        await callback.answer(str(error), show_alert=True)
        return
    except HabitArchivedError as error:
        await callback.answer(str(error), show_alert=True)
        return
    except HabitAlreadyCompletedError as error:
        await callback.answer(str(error), show_alert=True)
        return

    await callback.message.edit_text(
        _build_habit_card_text(habit_card),
        reply_markup=get_habit_card_keyboard(
            habit_card.id,
            callback_data.source,
            is_completed_today=habit_card.is_completed_today,
            is_active=habit_card.is_active,
        ),
    )
    await callback.answer("Отмечено на сегодня.")


@router.callback_query(HabitStatsCallback.filter())
async def show_habit_stats(
    callback: CallbackQuery,
    callback_data: HabitStatsCallback,
    user_service: UserService,
    habit_service: HabitService,
) -> None:
    if callback.from_user is None or callback.message is None:
        await callback.answer()
        return

    user = await user_service.get_by_telegram_id(callback.from_user.id)
    if user is None:
        await callback.answer("Сначала отправьте /start.", show_alert=True)
        return

    try:
        stats = await habit_service.get_habit_stats(user.id, callback_data.habit_id)
    except HabitNotFoundError:
        await callback.answer("Привычка не найдена.", show_alert=True)
        return
    except HabitDeletedError as error:
        await callback.answer(str(error), show_alert=True)
        return

    await callback.message.edit_text(
        _build_habit_stats_text(stats),
        reply_markup=get_habit_stats_keyboard(
            stats.id,
            callback_data.source,
        ),
    )
    await callback.answer()


@router.callback_query(HabitArchiveCallback.filter())
async def archive_habit(
    callback: CallbackQuery,
    callback_data: HabitArchiveCallback,
    user_service: UserService,
    habit_service: HabitService,
) -> None:
    if callback.from_user is None or callback.message is None:
        await callback.answer()
        return

    user = await user_service.get_by_telegram_id(callback.from_user.id)
    if user is None:
        await callback.answer("Сначала отправьте /start.", show_alert=True)
        return

    try:
        await habit_service.archive_habit(user.id, callback_data.habit_id)
    except HabitNotFoundError:
        await callback.answer("Привычка не найдена.", show_alert=True)
        return
    except HabitDeletedError as error:
        await callback.answer(str(error), show_alert=True)
        return

    if callback_data.source == HabitListSource.TODAY.value:
        text, reply_markup = await _build_today_screen(user.id, habit_service)
    else:
        text, reply_markup = await _build_active_screen(user.id, habit_service)

    await callback.message.edit_text(text, reply_markup=reply_markup)
    await callback.answer("Привычка архивирована.")


@router.callback_query(HabitRestoreCallback.filter())
async def restore_habit(
    callback: CallbackQuery,
    callback_data: HabitRestoreCallback,
    user_service: UserService,
    habit_service: HabitService,
) -> None:
    if callback.from_user is None or callback.message is None:
        await callback.answer()
        return

    user = await user_service.get_by_telegram_id(callback.from_user.id)
    if user is None:
        await callback.answer("Сначала отправьте /start.", show_alert=True)
        return

    try:
        await habit_service.restore_habit(user.id, callback_data.habit_id)
    except HabitNotFoundError:
        await callback.answer("Привычка не найдена.", show_alert=True)
        return
    except HabitDeletedError as error:
        await callback.answer(str(error), show_alert=True)
        return

    text, reply_markup = await _build_archive_screen(user.id, habit_service)
    await callback.message.edit_text(text, reply_markup=reply_markup)
    await callback.answer("Привычка снова активна.")


@router.callback_query(HabitDeleteCallback.filter())
async def delete_habit(
    callback: CallbackQuery,
    callback_data: HabitDeleteCallback,
    user_service: UserService,
    habit_service: HabitService,
) -> None:
    if callback.from_user is None or callback.message is None:
        await callback.answer()
        return

    user = await user_service.get_by_telegram_id(callback.from_user.id)
    if user is None:
        await callback.answer("Сначала отправьте /start.", show_alert=True)
        return

    try:
        await habit_service.soft_delete_habit(user.id, callback_data.habit_id)
    except HabitNotFoundError:
        await callback.answer("Привычка не найдена.", show_alert=True)
        return
    except HabitDeletedError as error:
        await callback.answer(str(error), show_alert=True)
        return

    if callback_data.source == HabitListSource.TODAY.value:
        text, reply_markup = await _build_today_screen(user.id, habit_service)
    elif callback_data.source == HabitListSource.ARCHIVE.value:
        text, reply_markup = await _build_archive_screen(user.id, habit_service)
    else:
        text, reply_markup = await _build_active_screen(user.id, habit_service)

    await callback.message.edit_text(text, reply_markup=reply_markup)
    await callback.answer("Привычка удалена.")


async def _build_active_screen(
    user_id: int,
    habit_service: HabitService,
) -> tuple[str, InlineKeyboardMarkup | None]:
    habits = await habit_service.get_active_habits(user_id)
    if habits:
        return (
            "Твои активные привычки:\nВыбери привычку, чтобы открыть карточку.",
            get_habits_list_keyboard(
                habits,
                HabitListSource.LIST.value,
                show_archive_switch=True,
            ),
        )

    archived_habits = await habit_service.get_archived_habits(user_id)
    if archived_habits:
        return (
            "Активных привычек пока нет. Но у тебя есть привычки в архиве.",
            get_habits_list_keyboard(
                archived_habits,
                HabitListSource.ARCHIVE.value,
                show_back_to_active=True,
            ),
        )

    return ("У тебя пока нет активных привычек.", None)


async def _build_archive_screen(
    user_id: int,
    habit_service: HabitService,
) -> tuple[str, InlineKeyboardMarkup | None]:
    habits = await habit_service.get_archived_habits(user_id)
    if not habits:
        return (
            "Архив пуст. Здесь будут привычки, которые ты архивировал.",
            get_habits_list_keyboard(
                [],
                HabitListSource.ARCHIVE.value,
                show_back_to_active=True,
            ),
        )

    return (
        "Архив привычек:\nЗдесь можно открыть привычку и вернуть её в активные.",
        get_habits_list_keyboard(
            habits,
            HabitListSource.ARCHIVE.value,
            show_back_to_active=True,
        ),
    )


async def _build_today_screen(
    user_id: int,
    habit_service: HabitService,
) -> tuple[str, InlineKeyboardMarkup | None]:
    habits = await habit_service.get_today_habits(user_id)
    if not habits:
        return ("У тебя пока нет активных привычек на сегодня.", None)

    return (
        "Сегодня:\nВыбери привычку, чтобы открыть карточку.",
        get_habits_list_keyboard(
            habits,
            HabitListSource.TODAY.value,
            show_completion_status=True,
        ),
    )


def _build_habit_card_text(habit_card: HabitCard) -> str:
    today_status = "Выполнена" if habit_card.is_completed_today else "Не выполнена"
    active_status = "Активная" if habit_card.is_active else "В архиве"
    reminder_status = (
        habit_card.reminder_time.strftime("%H:%M")
        if habit_card.reminder_enabled and habit_card.reminder_time is not None
        else "Выключено"
    )
    return "\n".join(
        [
            f"📌 {html.quote(habit_card.title)}",
            "",
            f"Сегодня: {today_status}",
            f"Всего выполнений: {habit_card.total_completions}",
            f"Текущая серия: {habit_card.current_streak}",
            f"Лучшая серия: {habit_card.best_streak}",
            f"Напоминание: {reminder_status}",
            f"Статус: {active_status}",
        ]
    )


def _build_habit_stats_text(stats: HabitStats) -> str:
    today_status = "Да" if stats.is_completed_today else "Нет"
    created_at = stats.created_at.strftime("%d.%m.%Y %H:%M UTC")
    return "\n".join(
        [
            f"📈 Статистика: {html.quote(stats.title)}",
            "",
            f"Всего выполнений: {stats.total_completions}",
            f"Выполнена сегодня: {today_status}",
            f"Текущая серия: {stats.current_streak}",
            f"Лучшая серия: {stats.best_streak}",
            "",
            "Последние 7 дней:",
            stats.last_7_days_progress_text,
            "",
            f"Дата создания: {created_at}",
        ]
    )
