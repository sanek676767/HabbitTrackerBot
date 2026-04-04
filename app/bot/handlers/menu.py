from aiogram import F, Router
from aiogram import html
from aiogram.types import Message

from app.bot.keyboards import ADD_HABIT_BUTTON, MY_HABITS_BUTTON, PROFILE_BUTTON, get_main_menu_keyboard
from app.services.user_service import UserService


router = Router(name="menu")


@router.message(F.text == ADD_HABIT_BUTTON)
async def add_habit_handler(message: Message, user_service: UserService) -> None:
    if message.from_user is None:
        await message.answer("Не удалось определить пользователя Telegram.")
        return

    user = await user_service.get_by_telegram_id(message.from_user.id)
    if user is None:
        await message.answer("Сначала отправьте /start.", reply_markup=get_main_menu_keyboard())
        return

    await message.answer(
        "Добавление привычек будет следующим шагом MVP. Сейчас доступны профиль и базовая инфраструктура.",
        reply_markup=get_main_menu_keyboard(),
    )


@router.message(F.text == MY_HABITS_BUTTON)
async def my_habits_handler(message: Message, user_service: UserService) -> None:
    if message.from_user is None:
        await message.answer("Не удалось определить пользователя Telegram.")
        return

    user = await user_service.get_by_telegram_id(message.from_user.id)
    if user is None:
        await message.answer("Сначала отправьте /start.", reply_markup=get_main_menu_keyboard())
        return

    await message.answer(
        "Список привычек пока не реализован. На этом этапе можно проверить регистрацию через /profile.",
        reply_markup=get_main_menu_keyboard(),
    )


@router.message(F.text == PROFILE_BUTTON)
async def profile_shortcut_handler(message: Message, user_service: UserService) -> None:
    if message.from_user is None:
        await message.answer("Не удалось определить пользователя Telegram.")
        return

    user = await user_service.get_by_telegram_id(message.from_user.id)
    if user is None:
        await message.answer("Пользователь не найден. Сначала отправьте /start.")
        return

    username = f"@{user.username}" if user.username else "не указан"
    created_at = user.created_at.strftime("%Y-%m-%d %H:%M:%S %Z").strip()
    admin_status = "yes" if user.is_admin else "no"

    await message.answer(
        "\n".join(
            [
                "Профиль:",
                f"telegram_id: {user.telegram_id}",
                f"username: {html.quote(username)}",
                f"registered_at: {created_at}",
                f"is_admin: {admin_status}",
            ]
        ),
        reply_markup=get_main_menu_keyboard(),
    )
