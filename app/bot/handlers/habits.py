from aiogram import F, Router, html
from aiogram.types import CallbackQuery, InlineKeyboardMarkup, Message

from app.bot.callbacks import (
    HabitArchiveCallback,
    HabitDeleteCallback,
    HabitDeleteConfirmCallback,
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
    get_habit_delete_confirm_keyboard,
    get_habit_stats_keyboard,
    get_habits_list_keyboard,
)
from app.services.habit_service import (
    HabitAlreadyCompletedError,
    HabitArchivedError,
    HabitCard,
    HabitDeletedError,
    HabitNotDueTodayError,
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
        await message.answer("Не удалось определить пользователя.")
        return

    user = await user_service.get_by_telegram_id(message.from_user.id)
    if user is None:
        await message.answer("Сначала отправь /start.")
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
        await callback.answer("Сначала отправь /start.", show_alert=True)
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
        await callback.answer("Сначала отправь /start.", show_alert=True)
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
            is_due_today=habit_card.is_due_today,
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
        await callback.answer("Сначала отправь /start.", show_alert=True)
        return

    try:
        habit_card = await habit_service.complete_habit_for_today(user.id, callback_data.habit_id)
    except HabitNotFoundError:
        await callback.answer("Привычка не найдена.", show_alert=True)
        return
    except HabitDeletedError as error:
        await callback.answer(str(error), show_alert=True)
        return
    except (HabitArchivedError, HabitAlreadyCompletedError, HabitNotDueTodayError) as error:
        await callback.answer(str(error), show_alert=True)
        return

    await callback.message.edit_text(
        _build_habit_card_text(habit_card),
        reply_markup=get_habit_card_keyboard(
            habit_card.id,
            callback_data.source,
            is_completed_today=habit_card.is_completed_today,
            is_active=habit_card.is_active,
            is_due_today=habit_card.is_due_today,
        ),
    )
    await callback.answer("Готово.")


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
        await callback.answer("Сначала отправь /start.", show_alert=True)
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
        reply_markup=get_habit_stats_keyboard(stats.id, callback_data.source),
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
        await callback.answer("Сначала отправь /start.", show_alert=True)
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
    await callback.answer("Привычка перенесена в архив.")


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
        await callback.answer("Сначала отправь /start.", show_alert=True)
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
    await callback.answer("Привычка снова в активных.")


@router.callback_query(HabitDeleteCallback.filter())
async def ask_delete_habit(
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
        await callback.answer("Сначала отправь /start.", show_alert=True)
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
        _build_delete_confirm_text(habit_card),
        reply_markup=get_habit_delete_confirm_keyboard(habit_card.id, callback_data.source),
    )
    await callback.answer()


@router.callback_query(HabitDeleteConfirmCallback.filter())
async def delete_habit(
    callback: CallbackQuery,
    callback_data: HabitDeleteConfirmCallback,
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
            "📋 Мои привычки\n\nОткрой привычку, чтобы посмотреть карточку.",
            get_habits_list_keyboard(
                habits,
                HabitListSource.LIST.value,
                show_archive_switch=True,
            ),
        )

    archived_habits = await habit_service.get_archived_habits(user_id)
    if archived_habits:
        return (
            "Активных привычек пока нет.\n\nНиже можно открыть архив.",
            get_habits_list_keyboard(
                archived_habits,
                HabitListSource.ARCHIVE.value,
                show_back_to_active=True,
            ),
        )

    return ("Пока нет ни одной привычки. Начни с кнопки «➕ Добавить привычку».", None)


async def _build_archive_screen(
    user_id: int,
    habit_service: HabitService,
) -> tuple[str, InlineKeyboardMarkup | None]:
    habits = await habit_service.get_archived_habits(user_id)
    if not habits:
        return (
            "🗂 Архив пока пуст.",
            get_habits_list_keyboard(
                [],
                HabitListSource.ARCHIVE.value,
                show_back_to_active=True,
            ),
        )

    return (
        "🗂 Архив\n\nЗдесь лежат привычки, которые ты убрал из активных.",
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
        return ("Сегодня по расписанию привычек нет.", None)

    return (
        "🔥 Сегодня\n\nЗдесь только то, что запланировано на сегодня.",
        get_habits_list_keyboard(
            habits,
            HabitListSource.TODAY.value,
            show_completion_status=True,
        ),
    )


def _build_habit_card_text(habit_card: HabitCard) -> str:
    if habit_card.is_completed_today:
        today_status = "выполнена"
    elif habit_card.is_due_today:
        today_status = "ждёт отметку"
    else:
        today_status = "на сегодня не запланирована"

    reminder_status = (
        habit_card.reminder_time.strftime("%H:%M")
        if habit_card.reminder_enabled and habit_card.reminder_time is not None
        else "выключено"
    )
    active_status = "активна" if habit_card.is_active else "в архиве"
    return "\n".join(
        [
            f"📌 {html.quote(habit_card.title)}",
            "",
            f"Частота: {habit_card.frequency_text}",
            f"Сегодня: {today_status}",
            f"Текущая серия: {habit_card.current_streak}",
            f"Лучшая серия: {habit_card.best_streak}",
            f"Всего отметок: {habit_card.total_completions}",
            f"Напоминание: {reminder_status}",
            f"Статус: {active_status}",
        ]
    )


def _build_habit_stats_text(stats: HabitStats) -> str:
    today_due_text = "да" if stats.is_due_today else "нет"
    today_done_text = "да" if stats.is_completed_today else "нет"
    created_at = stats.created_at.strftime("%d.%m.%Y %H:%M")
    return "\n".join(
        [
            f"📊 {html.quote(stats.title)}",
            "",
            f"Частота: {stats.frequency_text}",
            f"Есть в плане на сегодня: {today_due_text}",
            f"Отмечена сегодня: {today_done_text}",
            f"Текущая серия: {stats.current_streak}",
            f"Лучшая серия: {stats.best_streak}",
            f"Всего отметок: {stats.total_completions}",
            "",
            "Последние 7 дней:",
            stats.last_7_days_progress_text,
            "",
            f"Создана: {created_at}",
        ]
    )


def _build_delete_confirm_text(habit_card: HabitCard) -> str:
    return "\n".join(
        [
            f"🗑 Удалить привычку «{html.quote(habit_card.title)}»?",
            "",
            "Она исчезнет из твоих списков. Если понадобится, её сможет вернуть администратор.",
        ]
    )
