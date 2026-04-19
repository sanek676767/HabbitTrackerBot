import pytest

from app.bot.main import build_global_commands
from app.bot.keyboards.main_menu import ADMIN_BUTTON, get_main_menu_keyboard
from app.services.admin_service import AdminAccessDeniedError, AdminService
from app.services.user_service import UserService
from tests.helpers import make_user


class FakeUserRepository:
    def __init__(self, users) -> None:
        self._users = list(users)
        self._users_by_telegram_id = {user.telegram_id: user for user in users}

    async def get_by_telegram_id(self, telegram_id: int):
        return self._users_by_telegram_id.get(telegram_id)

    async def count_users(self) -> int:
        return len(self._users)

    async def count_admin_users(self) -> int:
        return sum(1 for user in self._users if user.is_admin)

    async def count_blocked_users(self) -> int:
        return sum(1 for user in self._users if user.is_blocked)


class FakeHabitRepository:
    async def count_deleted_habits(self, user_id: int | None = None) -> int:
        return 3


class FakeFeedbackRepository:
    async def count_unread_feedback(self) -> int:
        return 2


def test_user_access_helpers_and_admin_button_visibility() -> None:
    admin_user = make_user(is_admin=True, is_blocked=False)
    regular_user = make_user(is_admin=False, is_blocked=False)
    blocked_admin = make_user(is_admin=True, is_blocked=True)

    assert UserService.can_use_bot(None) is True
    assert UserService.can_use_bot(admin_user) is True
    assert UserService.can_use_bot(regular_user) is True
    assert UserService.can_use_bot(blocked_admin) is False

    assert UserService.should_show_admin_entry(admin_user) is True
    assert UserService.should_show_admin_entry(regular_user) is False
    assert UserService.should_show_admin_entry(blocked_admin) is False
    assert UserService.should_show_admin_entry(None) is False

    hidden_keyboard = get_main_menu_keyboard(show_admin_button=False)
    visible_keyboard = get_main_menu_keyboard(show_admin_button=True)

    assert ADMIN_BUTTON not in _flatten_button_texts(hidden_keyboard)
    assert ADMIN_BUTTON in _flatten_button_texts(visible_keyboard)


def test_admin_command_is_not_exposed_in_global_commands() -> None:
    commands = build_global_commands()

    assert [command.command for command in commands] == [
        "start",
        "help",
        "profile",
        "feedback",
    ]


@pytest.mark.asyncio
async def test_admin_service_allows_only_unblocked_admin(dummy_session) -> None:
    admin_user = make_user(id=1, telegram_id=5001, username="chief", is_admin=True)
    regular_user = make_user(id=2, telegram_id=5002, username="reader", is_admin=False)
    blocked_admin = make_user(
        id=3,
        telegram_id=5003,
        username="blockedchief",
        is_admin=True,
        is_blocked=True,
    )
    user_repository = FakeUserRepository([admin_user, regular_user, blocked_admin])
    service = AdminService(
        session=dummy_session,
        user_repository=user_repository,
        habit_repository=FakeHabitRepository(),
        feedback_repository=FakeFeedbackRepository(),
        admin_action_log_service=None,
    )

    dashboard = await service.get_dashboard(admin_user.telegram_id)

    assert dashboard.total_users_count == 3
    assert dashboard.admin_users_count == 2
    assert dashboard.blocked_users_count == 1
    assert dashboard.deleted_habits_count == 3
    assert dashboard.unread_feedback_count == 2

    with pytest.raises(AdminAccessDeniedError):
        await service.get_dashboard(regular_user.telegram_id)

    with pytest.raises(AdminAccessDeniedError):
        await service.get_dashboard(blocked_admin.telegram_id)


def _flatten_button_texts(keyboard) -> list[str]:
    return [
        button.text
        for row in keyboard.keyboard
        for button in row
    ]
