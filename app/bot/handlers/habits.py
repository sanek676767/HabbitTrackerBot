from aiogram import F, Router, html
from aiogram.types import CallbackQuery, Message

from app.bot.callbacks import (
    HabitArchiveCallback,
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

    habits = await habit_service.get_active_habits(user.id)
    if not habits:
        archived_habits = await habit_service.get_archived_habits(user.id)
        if archived_habits:
            await message.answer(
                "Активных привычек пока нет. Но у тебя есть привычки в архиве.",
                reply_markup=get_habits_list_keyboard(
                    archived_habits,
                    HabitListSource.ARCHIVE.value,
                    show_back_to_active=True,
                ),
            )
            return
        await message.answer("У тебя пока нет активных привычек.")
        return

    await message.answer(
        _build_habits_list_text(),
        reply_markup=get_habits_list_keyboard(
            habits,
            HabitListSource.LIST.value,
            show_archive_switch=True,
        ),
    )


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
        habits = await habit_service.get_today_habits(user.id)
        if not habits:
            await callback.message.edit_text("У тебя пока нет активных привычек на сегодня.")
            await callback.answer()
            return

        await callback.message.edit_text(
            _build_today_text(),
            reply_markup=get_habits_list_keyboard(
                habits,
                HabitListSource.TODAY.value,
                show_completion_status=True,
            ),
        )
        await callback.answer()
        return

    if callback_data.source == HabitListSource.ARCHIVE.value:
        habits = await habit_service.get_archived_habits(user.id)
        if not habits:
            await callback.message.edit_text(
                "Архив пуст. Здесь будут привычки, которые ты архивировал.",
                reply_markup=get_habits_list_keyboard(
                    [],
                    HabitListSource.ARCHIVE.value,
                    show_back_to_active=True,
                ),
            )
            await callback.answer()
            return

        await callback.message.edit_text(
            _build_archive_list_text(),
            reply_markup=get_habits_list_keyboard(
                habits,
                HabitListSource.ARCHIVE.value,
                show_back_to_active=True,
            ),
        )
        await callback.answer()
        return

    habits = await habit_service.get_active_habits(user.id)
    if not habits:
        await callback.message.edit_text("У тебя пока нет активных привычек.")
        await callback.answer()
        return

    await callback.message.edit_text(
        _build_habits_list_text(),
        reply_markup=get_habits_list_keyboard(
            habits,
            HabitListSource.LIST.value,
            show_archive_switch=True,
        ),
    )
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

    if callback_data.source == HabitListSource.TODAY.value:
        habits = await habit_service.get_today_habits(user.id)
        if not habits:
            await callback.message.edit_text("У тебя пока нет активных привычек на сегодня.")
        else:
            await callback.message.edit_text(
                _build_today_text(),
                reply_markup=get_habits_list_keyboard(
                    habits,
                    HabitListSource.TODAY.value,
                    show_completion_status=True,
                ),
            )
    else:
        habits = await habit_service.get_active_habits(user.id)
        if not habits:
            await callback.message.edit_text("У тебя пока нет активных привычек.")
        else:
            await callback.message.edit_text(
                _build_habits_list_text(),
                reply_markup=get_habits_list_keyboard(
                    habits,
                    HabitListSource.LIST.value,
                ),
            )

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

    habits = await habit_service.get_archived_habits(user.id)
    if not habits:
        await callback.message.edit_text(
            "Архив пуст. Привычка возвращена в активные.",
            reply_markup=get_habits_list_keyboard(
                [],
                HabitListSource.ARCHIVE.value,
                show_back_to_active=True,
            ),
        )
    else:
        await callback.message.edit_text(
            _build_archive_list_text(),
            reply_markup=get_habits_list_keyboard(
                habits,
                HabitListSource.ARCHIVE.value,
                show_back_to_active=True,
            ),
        )

    await callback.answer("Привычка снова активна.")


def _build_habits_list_text() -> str:
    return "Твои активные привычки:\nВыбери привычку, чтобы открыть карточку."


def _build_archive_list_text() -> str:
    return "Архив привычек:\nЗдесь можно открыть привычку и вернуть её в активные."


def _build_today_text() -> str:
    return "Сегодня:\nВыбери привычку, чтобы открыть карточку."


def _build_habit_card_text(habit_card: HabitCard) -> str:
    today_status = "Выполнена" if habit_card.is_completed_today else "Не выполнена"
    active_status = "Активная" if habit_card.is_active else "В архиве"
    return "\n".join(
        [
            f"📌 {html.quote(habit_card.title)}",
            "",
            f"Сегодня: {today_status}",
            f"Всего выполнений: {habit_card.total_completions}",
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
            f"Дата создания: {created_at}",
        ]
    )
