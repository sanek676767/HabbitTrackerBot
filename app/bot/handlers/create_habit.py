from aiogram import F, Router, html
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import CallbackQuery, Message

from app.bot.callbacks import CreateHabitCallback
from app.bot.keyboards import (
    ADD_HABIT_BUTTON,
    ALL_MAIN_MENU_BUTTONS,
    BACK_TO_MENU_BUTTON,
    get_create_habit_keyboard,
    get_main_menu_keyboard,
)
from app.services.habit_service import HabitService, HabitValidationError
from app.services.user_service import UserService


router = Router(name="create_habit")


class CreateHabitStates(StatesGroup):
    waiting_for_title = State()


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
        await message.answer("Сначала отправьте /start.")
        return

    await state.set_state(CreateHabitStates.waiting_for_title)
    await message.answer(
        "Введите название привычки:",
        reply_markup=get_create_habit_keyboard(),
    )


@router.callback_query(
    CreateHabitStates.waiting_for_title,
    CreateHabitCallback.filter(F.action == "cancel"),
)
async def cancel_create_habit_from_button(
    callback: CallbackQuery,
    state: FSMContext,
) -> None:
    await state.clear()
    if callback.message is not None:
        await callback.message.edit_text("Создание привычки отменено.")
        await callback.message.answer(
            "Возвращаю в главное меню.",
            reply_markup=get_main_menu_keyboard(),
        )
    await callback.answer()


@router.message(CreateHabitStates.waiting_for_title, F.text == BACK_TO_MENU_BUTTON)
async def cancel_create_habit(
    message: Message,
    state: FSMContext,
) -> None:
    await state.clear()
    await message.answer(
        "Создание привычки отменено.",
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
            "Сначала заверши создание привычки или нажми «⬅️ Назад».",
            reply_markup=get_create_habit_keyboard(),
        )
        return

    user = await user_service.get_by_telegram_id(message.from_user.id)
    if user is None:
        await state.clear()
        await message.answer("Сначала отправьте /start.", reply_markup=get_main_menu_keyboard())
        return

    try:
        habit = await habit_service.create_habit(user.id, message.text or "")
    except HabitValidationError as error:
        await message.answer(
            str(error),
            reply_markup=get_create_habit_keyboard(),
        )
        return

    await state.clear()
    await message.answer(
        f"Привычка «{html.quote(habit.title)}» добавлена.",
        reply_markup=get_main_menu_keyboard(),
    )
