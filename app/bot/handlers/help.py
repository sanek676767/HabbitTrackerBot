from aiogram import F, Router
from aiogram.filters import Command
from aiogram.types import Message

from app.bot.keyboards import HELP_BUTTON, get_main_menu_keyboard


router = Router(name="help")


@router.message(Command("help"))
@router.message(F.text == HELP_BUTTON)
async def help_handler(message: Message) -> None:
    await message.answer(
        _build_help_text(),
        reply_markup=get_main_menu_keyboard(),
    )


def _build_help_text() -> str:
    return "\n".join(
        [
            "❓ Помощь",
            "",
            "Что умеет бот:",
            "• вести список ежедневных привычек",
            "• отмечать выполнение на сегодня",
            "• напоминать в нужное время",
            "• показывать streak и общий прогресс",
            "",
            "Как начать:",
            "• нажми «➕ Добавить привычку» и введи название",
            "• открой «🔥 Сегодня», чтобы быстро отмечать выполнение",
            "",
            "Как работают reminders:",
            "• открой карточку привычки",
            "• нажми «⏰ Напоминание»",
            "• сначала укажи своё текущее время, потом время напоминания",
            "",
            "Что такое streak:",
            "• текущая серия — сколько дней подряд привычка идёт без пропуска",
            "• лучшая серия — самый длинный такой отрезок",
            "",
            "Где архив:",
            "• открой «📋 Мои привычки»",
            "• перейди в «🗂 Архив», если привычка была архивирована",
            "",
            "Что показывает экран «📈 Прогресс»:",
            "• сколько привычек активно",
            "• сколько выполнено сегодня",
            "• completion rate за 7 и 30 дней",
            "• лучший текущий streak и последнюю активность",
        ]
    )
