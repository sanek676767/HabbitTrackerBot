from datetime import date

from aiogram import F, Router, html
from aiogram.exceptions import TelegramBadRequest
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import CallbackQuery, InlineKeyboardMarkup, Message

from app.bot.callbacks import CreateHabitCallback
from app.bot.keyboards import (
    ADD_HABIT_BUTTON,
    ALL_MAIN_MENU_BUTTONS,
    BACK_TO_MENU_BUTTON,
    get_create_habit_cancel_keyboard,
    get_create_habit_confirm_keyboard,
    get_create_habit_frequency_keyboard,
    get_create_habit_reminder_keyboard,
    get_create_habit_text_input_keyboard,
    get_create_habit_weekdays_keyboard,
    get_main_menu_keyboard,
)
from app.services.habit_schedule_service import HabitScheduleService
from app.services.habit_service import (
    HabitReminderValidationError,
    HabitService,
    HabitValidationError,
)
from app.services.user_service import UserService, UserTimeValidationError


router = Router(name="create_habit")


class CreateHabitStates(StatesGroup):
    waiting_for_title = State()
    choosing_frequency = State()
    choosing_weekdays = State()
    choosing_reminder = State()
    waiting_for_current_time = State()
    waiting_for_reminder_time = State()
    confirming = State()


@router.message(F.text == ADD_HABIT_BUTTON)
async def start_create_habit(
    message: Message,
    state: FSMContext,
    user_service: UserService,
) -> None:
    if message.from_user is None:
        await message.answer("Не удалось определить пользователя Telegram.")
        return

    user = await user_service.get_by_telegram_id(message.from_user.id)
    if user is None:
        await message.answer("Сначала отправь /start.")
        return

    await state.clear()
    prompt_message = await message.answer(
        _build_title_prompt_text(),
        reply_markup=get_create_habit_cancel_keyboard(),
    )
    await state.set_state(CreateHabitStates.waiting_for_title)
    await state.update_data(
        title="",
        frequency_type=None,
        frequency_interval=None,
        week_days_mask=None,
        start_date=date.today().isoformat(),
        reminder_enabled=False,
        reminder_time=None,
        title_edit_mode="initial",
        chat_id=prompt_message.chat.id,
        prompt_chat_id=prompt_message.chat.id,
        prompt_message_id=prompt_message.message_id,
    )


@router.callback_query(CreateHabitCallback.filter(F.action == "cancel"))
async def cancel_create_habit(
    callback: CallbackQuery,
    state: FSMContext,
) -> None:
    await state.clear()
    if callback.message is not None:
        await callback.message.edit_text("Создание привычки остановлено.")
    await callback.answer()


@router.message(CreateHabitStates.waiting_for_title, F.text == BACK_TO_MENU_BUTTON)
async def cancel_create_habit_from_reply_button(
    message: Message,
    state: FSMContext,
) -> None:
    await state.clear()
    await message.answer(
        "Создание привычки остановлено.",
        reply_markup=get_main_menu_keyboard(),
    )


@router.message(CreateHabitStates.waiting_for_title)
async def save_habit_title(
    message: Message,
    state: FSMContext,
    user_service: UserService,
    habit_service: HabitService,
) -> None:
    if message.from_user is None:
        await message.answer("Не удалось определить пользователя Telegram.")
        return

    if (message.text or "") in ALL_MAIN_MENU_BUTTONS:
        await message.answer(
            "Сначала напиши название привычки или нажми «Назад».",
            reply_markup=get_main_menu_keyboard(),
        )
        return

    user = await user_service.get_by_telegram_id(message.from_user.id)
    if user is None:
        await state.clear()
        await message.answer(
            "Сначала отправь /start.",
            reply_markup=get_main_menu_keyboard(),
        )
        return

    try:
        normalized_title = habit_service.validate_title(message.text or "")
    except HabitValidationError as error:
        await message.answer(str(error))
        return

    state_data = await state.get_data()
    title_edit_mode = state_data.get("title_edit_mode")
    await state.update_data(title=normalized_title, title_edit_mode="confirm")

    if title_edit_mode == "confirm" and state_data.get("frequency_type"):
        await state.set_state(CreateHabitStates.confirming)
        await _render_flow_message(
            bot=message.bot,
            state=state,
            text=_build_confirmation_text(await state.get_data(), habit_service),
            reply_markup=get_create_habit_confirm_keyboard(),
        )
        await message.answer(f"Название обновил: «{html.quote(normalized_title)}».")
        return

    await state.set_state(CreateHabitStates.choosing_frequency)
    await _render_flow_message(
        bot=message.bot,
        state=state,
        text=_build_frequency_prompt_text(normalized_title),
        reply_markup=get_create_habit_frequency_keyboard(),
    )


@router.callback_query(CreateHabitStates.choosing_frequency, CreateHabitCallback.filter())
async def handle_frequency_choice(
    callback: CallbackQuery,
    callback_data: CreateHabitCallback,
    state: FSMContext,
    habit_service: HabitService,
) -> None:
    if callback.message is None:
        await callback.answer()
        return

    state_data = await state.get_data()
    title = state_data.get("title") or ""
    start_date = _get_start_date(state_data)

    if callback_data.action == "freq_daily":
        schedule = habit_service.build_schedule_config(
            frequency_type=HabitScheduleService.DAILY,
            start_date=start_date,
        )
        await state.update_data(
            frequency_type=schedule.frequency_type,
            frequency_interval=schedule.frequency_interval,
            week_days_mask=schedule.week_days_mask,
        )
        await state.set_state(CreateHabitStates.choosing_reminder)
        await callback.message.edit_text(
            _build_reminder_prompt_text(await state.get_data(), habit_service),
            reply_markup=get_create_habit_reminder_keyboard(reminder_enabled=False),
        )
        await callback.answer()
        return

    if callback_data.action == "freq_interval":
        schedule = habit_service.build_schedule_config(
            frequency_type=HabitScheduleService.INTERVAL,
            frequency_interval=HabitScheduleService.EVERY_OTHER_DAY_INTERVAL,
            start_date=start_date,
        )
        await state.update_data(
            frequency_type=schedule.frequency_type,
            frequency_interval=schedule.frequency_interval,
            week_days_mask=schedule.week_days_mask,
        )
        await state.set_state(CreateHabitStates.choosing_reminder)
        await callback.message.edit_text(
            _build_reminder_prompt_text(await state.get_data(), habit_service),
            reply_markup=get_create_habit_reminder_keyboard(reminder_enabled=False),
        )
        await callback.answer()
        return

    if callback_data.action == "freq_weekdays":
        await state.update_data(
            frequency_type=HabitScheduleService.WEEKDAYS,
            frequency_interval=None,
            week_days_mask=None,
        )
        await state.set_state(CreateHabitStates.choosing_weekdays)
        await callback.message.edit_text(
            _build_weekdays_prompt_text(title, []),
            reply_markup=get_create_habit_weekdays_keyboard([]),
        )
        await callback.answer()
        return

    await callback.answer()


@router.callback_query(CreateHabitStates.choosing_weekdays, CreateHabitCallback.filter())
async def handle_weekdays_choice(
    callback: CallbackQuery,
    callback_data: CreateHabitCallback,
    state: FSMContext,
    habit_service: HabitService,
) -> None:
    if callback.message is None:
        await callback.answer()
        return

    state_data = await state.get_data()
    title = state_data.get("title") or ""
    selected_days = HabitScheduleService.decode_week_days_mask(state_data.get("week_days_mask"))

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
        await callback.message.edit_text(
            _build_weekdays_prompt_text(title, selected_days),
            reply_markup=get_create_habit_weekdays_keyboard(selected_days),
        )
        await callback.answer()
        return

    if callback_data.action == "weekdays_done":
        try:
            schedule = habit_service.build_schedule_config(
                frequency_type=HabitScheduleService.WEEKDAYS,
                week_days_mask=state_data.get("week_days_mask"),
                start_date=_get_start_date(state_data),
            )
        except HabitValidationError as error:
            await callback.answer(str(error), show_alert=True)
            return

        await state.update_data(
            frequency_type=schedule.frequency_type,
            frequency_interval=schedule.frequency_interval,
            week_days_mask=schedule.week_days_mask,
        )
        await state.set_state(CreateHabitStates.choosing_reminder)
        await callback.message.edit_text(
            _build_reminder_prompt_text(await state.get_data(), habit_service),
            reply_markup=get_create_habit_reminder_keyboard(
                reminder_enabled=bool((await state.get_data()).get("reminder_enabled"))
            ),
        )
        await callback.answer()
        return

    if callback_data.action == "to_frequency":
        await state.set_state(CreateHabitStates.choosing_frequency)
        await callback.message.edit_text(
            _build_frequency_prompt_text(title),
            reply_markup=get_create_habit_frequency_keyboard(),
        )
        await callback.answer()
        return

    await callback.answer()


@router.callback_query(CreateHabitStates.choosing_reminder, CreateHabitCallback.filter())
async def handle_reminder_choice(
    callback: CallbackQuery,
    callback_data: CreateHabitCallback,
    state: FSMContext,
    user_service: UserService,
    habit_service: HabitService,
) -> None:
    if callback.from_user is None or callback.message is None:
        await callback.answer()
        return

    state_data = await state.get_data()
    title = state_data.get("title") or ""

    if callback_data.action == "to_frequency":
        await state.set_state(CreateHabitStates.choosing_frequency)
        await callback.message.edit_text(
            _build_frequency_prompt_text(title),
            reply_markup=get_create_habit_frequency_keyboard(),
        )
        await callback.answer()
        return

    if callback_data.action == "reminder_clear":
        await state.update_data(reminder_enabled=False, reminder_time=None)
        await callback.message.edit_text(
            _build_reminder_prompt_text(await state.get_data(), habit_service),
            reply_markup=get_create_habit_reminder_keyboard(reminder_enabled=False),
        )
        await callback.answer("Напоминание убрал.")
        return

    if callback_data.action == "reminder_skip":
        await state.update_data(reminder_enabled=False, reminder_time=None)
        await state.set_state(CreateHabitStates.confirming)
        await callback.message.edit_text(
            _build_confirmation_text(await state.get_data(), habit_service),
            reply_markup=get_create_habit_confirm_keyboard(),
        )
        await callback.answer()
        return

    if callback_data.action == "reminder_next":
        if not state_data.get("reminder_enabled"):
            await callback.answer("Напоминание пока не настроено.", show_alert=True)
            return
        await state.set_state(CreateHabitStates.confirming)
        await callback.message.edit_text(
            _build_confirmation_text(await state.get_data(), habit_service),
            reply_markup=get_create_habit_confirm_keyboard(),
        )
        await callback.answer()
        return

    if callback_data.action == "reminder_setup":
        user = await user_service.get_by_telegram_id(callback.from_user.id)
        if user is None:
            await state.clear()
            await callback.answer("Сначала отправь /start.", show_alert=True)
            return

        if user.utc_offset_minutes is None:
            await state.set_state(CreateHabitStates.waiting_for_current_time)
            await callback.message.edit_text(
                _build_current_local_time_prompt_text(title),
                reply_markup=get_create_habit_text_input_keyboard(back_action="to_reminder"),
            )
            await callback.answer()
            return

        await state.set_state(CreateHabitStates.waiting_for_reminder_time)
        await callback.message.edit_text(
            _build_reminder_time_prompt_text(title, state_data.get("reminder_time")),
            reply_markup=get_create_habit_text_input_keyboard(back_action="to_reminder"),
        )
        await callback.answer()
        return

    await callback.answer()


@router.callback_query(CreateHabitStates.waiting_for_current_time, CreateHabitCallback.filter())
@router.callback_query(CreateHabitStates.waiting_for_reminder_time, CreateHabitCallback.filter())
async def handle_create_habit_text_step_callbacks(
    callback: CallbackQuery,
    callback_data: CreateHabitCallback,
    state: FSMContext,
    habit_service: HabitService,
) -> None:
    if callback.message is None:
        await callback.answer()
        return

    if callback_data.action != "to_reminder":
        await callback.answer()
        return

    await state.set_state(CreateHabitStates.choosing_reminder)
    await callback.message.edit_text(
        _build_reminder_prompt_text(await state.get_data(), habit_service),
        reply_markup=get_create_habit_reminder_keyboard(
            reminder_enabled=bool((await state.get_data()).get("reminder_enabled"))
        ),
    )
    await callback.answer()


@router.message(CreateHabitStates.waiting_for_current_time)
async def save_current_local_time_for_create_flow(
    message: Message,
    state: FSMContext,
    user_service: UserService,
) -> None:
    if message.from_user is None:
        await message.answer("Не удалось определить пользователя.")
        return

    if (message.text or "") in ALL_MAIN_MENU_BUTTONS:
        await message.answer("Пришли своё текущее местное время или нажми «Назад».")
        return

    user = await user_service.get_by_telegram_id(message.from_user.id)
    if user is None:
        await state.clear()
        await message.answer("Сначала отправь /start.")
        return

    try:
        await user_service.set_utc_offset_from_local_time(user.id, message.text or "")
    except UserTimeValidationError as error:
        await message.answer(str(error))
        return

    state_data = await state.get_data()
    title = state_data.get("title") or ""
    await state.set_state(CreateHabitStates.waiting_for_reminder_time)
    await _render_flow_message(
        bot=message.bot,
        state=state,
        text=_build_reminder_time_prompt_text(title, state_data.get("reminder_time")),
        reply_markup=get_create_habit_text_input_keyboard(back_action="to_reminder"),
    )
    await message.answer("Запомнил твоё местное время. Теперь укажи время напоминания.")


@router.message(CreateHabitStates.waiting_for_reminder_time)
async def save_reminder_time_for_create_flow(
    message: Message,
    state: FSMContext,
    user_service: UserService,
    habit_service: HabitService,
) -> None:
    if message.from_user is None:
        await message.answer("Не удалось определить пользователя.")
        return

    if (message.text or "") in ALL_MAIN_MENU_BUTTONS:
        await message.answer("Пришли время напоминания или нажми «Назад».")
        return

    user = await user_service.get_by_telegram_id(message.from_user.id)
    if user is None:
        await state.clear()
        await message.answer("Сначала отправь /start.")
        return

    try:
        reminder_time = habit_service.parse_reminder_time(message.text or "")
    except HabitReminderValidationError as error:
        await message.answer(str(error))
        return

    await state.update_data(
        reminder_enabled=True,
        reminder_time=reminder_time.strftime("%H:%M"),
    )
    await state.set_state(CreateHabitStates.confirming)
    await _render_flow_message(
        bot=message.bot,
        state=state,
        text=_build_confirmation_text(await state.get_data(), habit_service),
        reply_markup=get_create_habit_confirm_keyboard(),
    )
    await message.answer(f"Напоминание поставил на {reminder_time.strftime('%H:%M')}.")


@router.callback_query(CreateHabitStates.confirming, CreateHabitCallback.filter())
async def handle_create_confirmation(
    callback: CallbackQuery,
    callback_data: CreateHabitCallback,
    state: FSMContext,
    user_service: UserService,
    habit_service: HabitService,
) -> None:
    if callback.from_user is None or callback.message is None:
        await callback.answer()
        return

    state_data = await state.get_data()

    if callback_data.action == "edit_title":
        await state.set_state(CreateHabitStates.waiting_for_title)
        await state.update_data(title_edit_mode="confirm")
        await callback.message.edit_text(
            _build_title_prompt_text(current_title=state_data.get("title") or None),
            reply_markup=get_create_habit_cancel_keyboard(),
        )
        await callback.answer()
        return

    if callback_data.action == "edit_frequency":
        await state.set_state(CreateHabitStates.choosing_frequency)
        await callback.message.edit_text(
            _build_frequency_prompt_text(state_data.get("title") or ""),
            reply_markup=get_create_habit_frequency_keyboard(),
        )
        await callback.answer()
        return

    if callback_data.action == "edit_reminder":
        await state.set_state(CreateHabitStates.choosing_reminder)
        await callback.message.edit_text(
            _build_reminder_prompt_text(state_data, habit_service),
            reply_markup=get_create_habit_reminder_keyboard(
                reminder_enabled=bool(state_data.get("reminder_enabled"))
            ),
        )
        await callback.answer()
        return

    if callback_data.action != "confirm":
        await callback.answer()
        return

    user = await user_service.get_by_telegram_id(callback.from_user.id)
    if user is None:
        await state.clear()
        await callback.answer("Сначала отправь /start.", show_alert=True)
        return

    try:
        schedule = _build_schedule_from_state(state_data, habit_service)
        reminder_time = (
            habit_service.parse_reminder_time(state_data.get("reminder_time"))
            if state_data.get("reminder_enabled") and state_data.get("reminder_time")
            else None
        )
        habit = await habit_service.create_habit(
            user.id,
            state_data.get("title") or "",
            frequency_type=schedule.frequency_type,
            frequency_interval=schedule.frequency_interval,
            week_days_mask=schedule.week_days_mask,
            reminder_enabled=bool(state_data.get("reminder_enabled")),
            reminder_time=reminder_time,
            start_date=schedule.start_date,
        )
    except (HabitValidationError, HabitReminderValidationError) as error:
        await callback.answer(str(error), show_alert=True)
        return

    await state.clear()
    await callback.message.edit_text(
        _build_created_text(
            title=habit.title,
            frequency_text=habit_service.format_schedule(habit),
            reminder_enabled=habit.reminder_enabled,
            reminder_time=(
                habit.reminder_time.strftime("%H:%M")
                if habit.reminder_time is not None
                else None
            ),
        )
    )
    await callback.answer("Привычка создана.")


def _build_title_prompt_text(current_title: str | None = None) -> str:
    lines = [
        "➕ Новая привычка",
        "",
        "Напиши название привычки.",
    ]
    if current_title:
        lines.extend(
            [
                "",
                f"Сейчас: {html.quote(current_title)}",
            ]
        )
    return "\n".join(lines)


def _build_frequency_prompt_text(title: str) -> str:
    return "\n".join(
        [
            "🗓 Частота",
            "",
            f"Привычка: {html.quote(title)}",
            "Как часто она должна повторяться?",
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
            "Отметь дни, в которые привычка должна появляться.",
        ]
    )


def _build_reminder_prompt_text(state_data: dict, habit_service: HabitService) -> str:
    schedule = _build_schedule_from_state(state_data, habit_service)
    reminder_enabled = bool(state_data.get("reminder_enabled"))
    reminder_time = state_data.get("reminder_time")
    reminder_text = reminder_time if reminder_enabled and reminder_time else "выключено"
    return "\n".join(
        [
            "⏰ Напоминание",
            "",
            f"Привычка: {html.quote(state_data.get('title') or '')}",
            f"Частота: {habit_service.format_schedule_config(schedule)}",
            f"Напоминание: {reminder_text}",
            "",
            "Нужно напоминание для этой привычки?",
        ]
    )


def _build_current_local_time_prompt_text(title: str) -> str:
    return "\n".join(
        [
            "⏰ Настройка напоминания",
            "",
            f"Привычка: {html.quote(title)}",
            "Сначала напиши, сколько у тебя сейчас времени.",
            "Формат: ЧЧ:ММ",
            "Например: 21:35",
        ]
    )


def _build_reminder_time_prompt_text(title: str, current_time: str | None) -> str:
    lines = [
        "⏰ Время напоминания",
        "",
        f"Привычка: {html.quote(title)}",
        "Напиши время напоминания.",
        "Формат: ЧЧ:ММ",
        "Например: 09:30",
    ]
    if current_time:
        lines.extend(
            [
                "",
                f"Сейчас стоит: {current_time}",
            ]
        )
    return "\n".join(lines)


def _build_confirmation_text(state_data: dict, habit_service: HabitService) -> str:
    schedule = _build_schedule_from_state(state_data, habit_service)
    reminder_enabled = bool(state_data.get("reminder_enabled"))
    reminder_time = state_data.get("reminder_time")
    reminder_text = reminder_time if reminder_enabled and reminder_time else "выключено"
    return "\n".join(
        [
            "✅ Подтверждение",
            "",
            f"Название: {html.quote(state_data.get('title') or '')}",
            f"Частота: {habit_service.format_schedule_config(schedule)}",
            f"Напоминание: {reminder_text}",
            "",
            "Если всё верно, нажми «Создать».",
        ]
    )


def _build_created_text(
    *,
    title: str,
    frequency_text: str,
    reminder_enabled: bool,
    reminder_time: str | None,
) -> str:
    reminder_text = reminder_time if reminder_enabled and reminder_time else "выключено"
    return "\n".join(
        [
            f"Привычка «{html.quote(title)}» создана.",
            "",
            f"Частота: {frequency_text}",
            f"Напоминание: {reminder_text}",
        ]
    )


def _get_start_date(state_data: dict) -> date:
    raw_start_date = state_data.get("start_date")
    if isinstance(raw_start_date, str):
        return date.fromisoformat(raw_start_date)
    return date.today()


def _build_schedule_from_state(state_data: dict, habit_service: HabitService):
    return habit_service.build_schedule_config(
        frequency_type=state_data.get("frequency_type") or HabitScheduleService.DAILY,
        frequency_interval=state_data.get("frequency_interval"),
        week_days_mask=state_data.get("week_days_mask"),
        start_date=_get_start_date(state_data),
    )


async def _render_flow_message(
    *,
    bot,
    state: FSMContext,
    text: str,
    reply_markup: InlineKeyboardMarkup,
) -> tuple[int, int]:
    state_data = await state.get_data()
    prompt_chat_id = state_data.get("prompt_chat_id")
    prompt_message_id = state_data.get("prompt_message_id")

    if isinstance(prompt_chat_id, int) and isinstance(prompt_message_id, int):
        try:
            await bot.edit_message_text(
                chat_id=prompt_chat_id,
                message_id=prompt_message_id,
                text=text,
                reply_markup=reply_markup,
            )
            return prompt_chat_id, prompt_message_id
        except TelegramBadRequest:
            pass

    chat_id = state_data.get("chat_id")
    if not isinstance(chat_id, int):
        raise RuntimeError("Не удалось определить чат для экрана создания привычки.")

    sent_message = await bot.send_message(
        chat_id=chat_id,
        text=text,
        reply_markup=reply_markup,
    )
    await state.update_data(
        prompt_chat_id=sent_message.chat.id,
        prompt_message_id=sent_message.message_id,
    )
    return sent_message.chat.id, sent_message.message_id
