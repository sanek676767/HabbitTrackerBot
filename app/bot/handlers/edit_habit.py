from aiogram import F, Router, html
from aiogram.exceptions import TelegramBadRequest
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import CallbackQuery, Message

from app.bot.callbacks import HabitEditActionCallback, HabitEditCallback
from app.bot.habit_text import build_habit_card_text
from app.bot.keyboards import (
    ALL_MAIN_MENU_BUTTONS,
    get_habit_card_keyboard,
    get_habit_edit_frequency_keyboard,
    get_habit_edit_input_keyboard,
    get_habit_edit_keyboard,
    get_habit_edit_weekdays_keyboard,
)
from app.services.habit_schedule_service import HabitScheduleService
from app.services.habit_service import (
    HabitDeletedError,
    HabitNotFoundError,
    HabitService,
    HabitValidationError,
)
from app.services.user_service import UserService


router = Router(name="edit_habit")


class EditHabitStates(StatesGroup):
    waiting_for_title = State()
    choosing_frequency = State()
    choosing_weekdays = State()


@router.callback_query(HabitEditCallback.filter())
async def start_edit_habit(
    callback: CallbackQuery,
    callback_data: HabitEditCallback,
    state: FSMContext,
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

    await state.clear()
    await callback.message.edit_text(
        _build_edit_menu_text(
            habit_card.title,
            habit_card.frequency_text,
            habit_card.reminder_enabled,
            habit_card.reminder_time,
            habit_card.goal,
        ),
        reply_markup=get_habit_edit_keyboard(habit_card.id, callback_data.source),
    )
    await callback.answer()


@router.callback_query(HabitEditActionCallback.filter(F.action == "back"))
async def return_from_edit_menu(
    callback: CallbackQuery,
    callback_data: HabitEditActionCallback,
    state: FSMContext,
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

    await state.clear()
    await callback.message.edit_text(
        build_habit_card_text(habit_card),
        reply_markup=get_habit_card_keyboard(
            habit_card.id,
            callback_data.source,
            is_completed_today=habit_card.is_completed_today,
            is_active=habit_card.is_active,
            is_due_today=habit_card.is_due_today,
        ),
    )
    await callback.answer()


@router.callback_query(HabitEditActionCallback.filter(F.action == "title"))
async def start_title_edit(
    callback: CallbackQuery,
    callback_data: HabitEditActionCallback,
    state: FSMContext,
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

    await state.set_state(EditHabitStates.waiting_for_title)
    await state.update_data(
        habit_id=habit_card.id,
        source=callback_data.source,
        prompt_chat_id=callback.message.chat.id,
        prompt_message_id=callback.message.message_id,
    )
    await callback.message.edit_text(
        _build_title_prompt_text(habit_card.title),
        reply_markup=get_habit_edit_input_keyboard(habit_card.id, callback_data.source),
    )
    await callback.answer()


@router.message(EditHabitStates.waiting_for_title)
async def save_habit_title(
    message: Message,
    state: FSMContext,
    user_service: UserService,
    habit_service: HabitService,
) -> None:
    if message.from_user is None:
        await message.answer("Не удалось определить пользователя Telegram.")
        return

    user = await user_service.get_by_telegram_id(message.from_user.id)
    if user is None:
        await state.clear()
        await message.answer("Сначала отправь /start.")
        return

    if (message.text or "") in ALL_MAIN_MENU_BUTTONS:
        await message.answer("Напиши новое название или вернись назад кнопкой под сообщением.")
        return

    state_data = await state.get_data()
    habit_id = state_data.get("habit_id")
    source = state_data.get("source")
    prompt_chat_id = state_data.get("prompt_chat_id")
    prompt_message_id = state_data.get("prompt_message_id")

    if (
        not isinstance(habit_id, int)
        or not isinstance(source, str)
        or not isinstance(prompt_chat_id, int)
        or not isinstance(prompt_message_id, int)
    ):
        await state.clear()
        await message.answer("Не получилось продолжить редактирование. Открой привычку ещё раз.")
        return

    try:
        habit_card = await habit_service.rename_habit(user.id, habit_id, message.text or "")
    except HabitValidationError as error:
        await message.answer(str(error))
        return
    except HabitNotFoundError:
        await state.clear()
        await message.answer("Привычка не найдена.")
        return
    except HabitDeletedError as error:
        await state.clear()
        await message.answer(str(error))
        return

    await state.clear()
    await _render_card_message(
        bot=message.bot,
        chat_id=prompt_chat_id,
        message_id=prompt_message_id,
        habit_card=habit_card,
        source=source,
    )
    await message.answer(f"Название обновил: «{html.quote(habit_card.title)}».")


@router.callback_query(HabitEditActionCallback.filter(F.action == "frequency"))
async def open_frequency_edit(
    callback: CallbackQuery,
    callback_data: HabitEditActionCallback,
    state: FSMContext,
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

    await state.set_state(EditHabitStates.choosing_frequency)
    await state.update_data(
        habit_id=habit_card.id,
        source=callback_data.source,
        prompt_chat_id=callback.message.chat.id,
        prompt_message_id=callback.message.message_id,
    )
    await callback.message.edit_text(
        _build_frequency_prompt_text(habit_card.title, habit_card.frequency_text),
        reply_markup=get_habit_edit_frequency_keyboard(habit_card.id, callback_data.source),
    )
    await callback.answer()


@router.callback_query(EditHabitStates.choosing_frequency, HabitEditActionCallback.filter())
async def handle_frequency_edit(
    callback: CallbackQuery,
    callback_data: HabitEditActionCallback,
    state: FSMContext,
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

    if callback_data.action == "back":
        habit_card = await habit_service.get_habit_card(user.id, callback_data.habit_id)
        await state.clear()
        await callback.message.edit_text(
            _build_edit_menu_text(
                habit_card.title,
                habit_card.frequency_text,
                habit_card.reminder_enabled,
                habit_card.reminder_time,
                habit_card.goal,
            ),
            reply_markup=get_habit_edit_keyboard(habit_card.id, callback_data.source),
        )
        await callback.answer()
        return

    if callback_data.action == "freq_weekdays":
        try:
            schedule = await habit_service.get_habit_schedule_state(user.id, callback_data.habit_id)
            habit_card = await habit_service.get_habit_card(user.id, callback_data.habit_id)
        except HabitNotFoundError:
            await callback.answer("Привычка не найдена.", show_alert=True)
            return
        except HabitDeletedError as error:
            await callback.answer(str(error), show_alert=True)
            return

        selected_days = HabitScheduleService.decode_week_days_mask(schedule.week_days_mask)
        await state.set_state(EditHabitStates.choosing_weekdays)
        await state.update_data(week_days_mask=schedule.week_days_mask)
        await callback.message.edit_text(
            _build_weekdays_prompt_text(habit_card.title, selected_days),
            reply_markup=get_habit_edit_weekdays_keyboard(
                selected_days,
                callback_data.habit_id,
                callback_data.source,
            ),
        )
        await callback.answer()
        return

    if callback_data.action not in {"freq_daily", "freq_interval"}:
        await callback.answer()
        return

    frequency_type = HabitScheduleService.DAILY
    frequency_interval = None
    if callback_data.action == "freq_interval":
        frequency_type = HabitScheduleService.INTERVAL
        frequency_interval = HabitScheduleService.EVERY_OTHER_DAY_INTERVAL

    try:
        habit_card = await habit_service.update_habit_schedule(
            user.id,
            callback_data.habit_id,
            frequency_type=frequency_type,
            frequency_interval=frequency_interval,
        )
    except HabitValidationError as error:
        await callback.answer(str(error), show_alert=True)
        return
    except HabitNotFoundError:
        await callback.answer("Привычка не найдена.", show_alert=True)
        return
    except HabitDeletedError as error:
        await callback.answer(str(error), show_alert=True)
        return

    await state.clear()
    await callback.message.edit_text(
        build_habit_card_text(habit_card),
        reply_markup=get_habit_card_keyboard(
            habit_card.id,
            callback_data.source,
            is_completed_today=habit_card.is_completed_today,
            is_active=habit_card.is_active,
            is_due_today=habit_card.is_due_today,
        ),
    )
    await callback.answer("Частоту обновил.")


@router.callback_query(EditHabitStates.choosing_weekdays, HabitEditActionCallback.filter())
async def handle_weekdays_edit(
    callback: CallbackQuery,
    callback_data: HabitEditActionCallback,
    state: FSMContext,
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

    state_data = await state.get_data()
    selected_days = HabitScheduleService.decode_week_days_mask(state_data.get("week_days_mask"))

    if callback_data.action == "back_frequency":
        habit_card = await habit_service.get_habit_card(user.id, callback_data.habit_id)
        await state.set_state(EditHabitStates.choosing_frequency)
        await callback.message.edit_text(
            _build_frequency_prompt_text(habit_card.title, habit_card.frequency_text),
            reply_markup=get_habit_edit_frequency_keyboard(
                callback_data.habit_id,
                callback_data.source,
            ),
        )
        await callback.answer()
        return

    if callback_data.action.startswith("weekday_"):
        day_index = int(callback_data.action.split("_", maxsplit=1)[1])
        if day_index in selected_days:
            selected_days.remove(day_index)
        else:
            selected_days.append(day_index)
        selected_days.sort()
        week_days_mask = (
            HabitScheduleService.build_week_days_mask(selected_days)
            if selected_days
            else None
        )
        await state.update_data(week_days_mask=week_days_mask)
        habit_card = await habit_service.get_habit_card(user.id, callback_data.habit_id)
        await callback.message.edit_text(
            _build_weekdays_prompt_text(habit_card.title, selected_days),
            reply_markup=get_habit_edit_weekdays_keyboard(
                selected_days,
                callback_data.habit_id,
                callback_data.source,
            ),
        )
        await callback.answer()
        return

    if callback_data.action != "weekdays_done":
        await callback.answer()
        return

    try:
        habit_card = await habit_service.update_habit_schedule(
            user.id,
            callback_data.habit_id,
            frequency_type=HabitScheduleService.WEEKDAYS,
            week_days_mask=state_data.get("week_days_mask"),
        )
    except HabitValidationError as error:
        await callback.answer(str(error), show_alert=True)
        return
    except HabitNotFoundError:
        await callback.answer("Привычка не найдена.", show_alert=True)
        return
    except HabitDeletedError as error:
        await callback.answer(str(error), show_alert=True)
        return

    await state.clear()
    await callback.message.edit_text(
        build_habit_card_text(habit_card),
        reply_markup=get_habit_card_keyboard(
            habit_card.id,
            callback_data.source,
            is_completed_today=habit_card.is_completed_today,
            is_active=habit_card.is_active,
            is_due_today=habit_card.is_due_today,
        ),
    )
    await callback.answer("Частоту обновил.")


def _build_edit_menu_text(
    title: str,
    frequency_text: str,
    reminder_enabled: bool,
    reminder_time,
    goal,
) -> str:
    reminder_text = (
        reminder_time.strftime("%H:%M")
        if reminder_enabled and reminder_time is not None
        else "выключено"
    )
    goal_text = goal.goal_text if goal is not None else "не задана"
    return "\n".join(
        [
            f"✏️ Редактирование «{html.quote(title)}»",
            "",
            f"Частота: {frequency_text}",
            f"Напоминание: {reminder_text}",
            f"Цель: {goal_text}",
            "",
            "Выбери, что хочешь изменить.",
        ]
    )


def _build_title_prompt_text(title: str) -> str:
    return "\n".join(
        [
            "✏️ Изменение названия",
            "",
            f"Сейчас: {html.quote(title)}",
            "Напиши новое название.",
        ]
    )


def _build_frequency_prompt_text(title: str, frequency_text: str) -> str:
    return "\n".join(
        [
            "🗓 Изменение частоты",
            "",
            f"Привычка: {html.quote(title)}",
            f"Сейчас: {frequency_text}",
            "",
            "Выбери новый режим.",
        ]
    )


def _build_weekdays_prompt_text(title: str, selected_days: list[int]) -> str:
    selected_text = (
        HabitScheduleService.format_weekdays(
            HabitScheduleService.build_week_days_mask(selected_days)
        )
        if selected_days
        else "пока не выбраны"
    )
    return "\n".join(
        [
            "🗓 Дни недели",
            "",
            f"Привычка: {html.quote(title)}",
            f"Выбрано: {selected_text}",
            "",
            "Отметь нужные дни и нажми «Готово».",
        ]
    )


async def _render_card_message(
    *,
    bot,
    chat_id: int,
    message_id: int,
    habit_card,
    source: str,
) -> tuple[int, int]:
    try:
        await bot.edit_message_text(
            chat_id=chat_id,
            message_id=message_id,
            text=build_habit_card_text(habit_card),
            reply_markup=get_habit_card_keyboard(
                habit_card.id,
                source,
                is_completed_today=habit_card.is_completed_today,
                is_active=habit_card.is_active,
                is_due_today=habit_card.is_due_today,
            ),
        )
        return chat_id, message_id
    except TelegramBadRequest:
        sent_message = await bot.send_message(
            chat_id=chat_id,
            text=build_habit_card_text(habit_card),
            reply_markup=get_habit_card_keyboard(
                habit_card.id,
                source,
                is_completed_today=habit_card.is_completed_today,
                is_active=habit_card.is_active,
                is_due_today=habit_card.is_due_today,
            ),
        )
        return sent_message.chat.id, sent_message.message_id
