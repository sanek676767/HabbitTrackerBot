from aiogram import Router, html
from aiogram.filters import Command
from aiogram.types import Message

from app.bot.keyboards import get_main_menu_keyboard
from app.services.user_service import UserService


router = Router(name="profile")


@router.message(Command("profile"))
async def profile_handler(message: Message, user_service: UserService) -> None:
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
