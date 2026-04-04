from aiogram import Router, html
from aiogram.filters import CommandStart
from aiogram.types import Message

from app.bot.keyboards import get_main_menu_keyboard
from app.services.user_service import UserService


router = Router(name="start")


@router.message(CommandStart())
async def start_handler(message: Message, user_service: UserService) -> None:
    if message.from_user is None:
        await message.answer("Не удалось определить пользователя Telegram.")
        return

    user, is_created = await user_service.get_or_create_user(
        telegram_id=message.from_user.id,
        username=message.from_user.username,
        first_name=message.from_user.first_name,
        last_name=message.from_user.last_name,
    )

    greeting_name = html.quote(message.from_user.first_name or "пользователь")
    status_line = "Профиль создан." if is_created else "Профиль уже существует."

    await message.answer(
        "\n".join(
            [
                f"Привет, {greeting_name}.",
                status_line,
                f"Внутренний ID: {user.id}",
                "Команда /profile и кнопка «Профиль» покажут данные профиля.",
            ]
        ),
        reply_markup=get_main_menu_keyboard(),
    )
