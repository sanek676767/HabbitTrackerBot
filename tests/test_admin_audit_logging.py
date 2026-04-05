from datetime import datetime, timezone
from types import SimpleNamespace

import pytest

from app.services.admin_action_log_service import AdminActionLogService
from app.services.admin_service import AdminService
from app.services.feedback_service import FeedbackService
from tests.helpers import make_habit, make_user


class FakeUserRepository:
    def __init__(self, users) -> None:
        self.users_by_id = {user.id: user for user in users}
        self.users_by_telegram_id = {user.telegram_id: user for user in users}

    async def get_by_telegram_id(self, telegram_id: int):
        return self.users_by_telegram_id.get(telegram_id)

    async def get_by_id(self, user_id: int):
        return self.users_by_id.get(user_id)

    async def update_is_blocked(self, user, is_blocked: bool):
        user.is_blocked = is_blocked
        return user

    async def update_is_admin(self, user, is_admin: bool):
        user.is_admin = is_admin
        return user


class FakeHabitRepository:
    def __init__(self, deleted_habit=None) -> None:
        self.deleted_habit = deleted_habit

    async def count_active_habits(self, user_id: int) -> int:
        return 0

    async def count_archived_habits(self, user_id: int) -> int:
        return 0

    async def count_deleted_habits(self, user_id: int | None = None) -> int:
        return 0

    async def get_last_completed_habits_by_user(self, user_id: int, *, limit: int = 1):
        return []

    async def get_habit_by_id(self, habit_id: int):
        if self.deleted_habit is None or self.deleted_habit.id != habit_id:
            return None
        return self.deleted_habit

    async def restore_soft_deleted_habit(self, habit):
        habit.is_deleted = False
        habit.deleted_at = None
        habit.is_active = False
        return habit


class FakeFeedbackRepository:
    def __init__(self, feedback=None) -> None:
        self.feedback = feedback

    async def count_unread_feedback(self) -> int:
        return 0

    async def get_feedback_by_id(self, feedback_id: int):
        if self.feedback is None or self.feedback.id != feedback_id:
            return None
        return self.feedback

    async def save_admin_reply(self, feedback, reply_text: str, replied_at: datetime):
        feedback.admin_reply_text = reply_text
        feedback.admin_replied_at = replied_at
        feedback.is_read = True
        return feedback


class FakeAdminActionLogRepository:
    def __init__(self) -> None:
        self.logs = []

    async def create_log(
        self,
        *,
        actor_user_id: int,
        action_type: str,
        entity_type: str,
        target_user_id: int | None = None,
        entity_id: int | None = None,
        details_json: dict | None = None,
    ):
        log = SimpleNamespace(
            id=len(self.logs) + 1,
            actor_user_id=actor_user_id,
            target_user_id=target_user_id,
            action_type=action_type,
            entity_type=entity_type,
            entity_id=entity_id,
            details_json=details_json,
            created_at=datetime(2026, 4, 5, 23, 50, tzinfo=timezone.utc),
            actor_user=None,
            target_user=None,
        )
        self.logs.append(log)
        return log

    async def count_logs(self) -> int:
        return len(self.logs)

    async def list_logs(self, *, limit: int, offset: int):
        return list(reversed(self.logs))[offset : offset + limit]

    async def list_logs_by_actor(self, actor_user_id: int, *, limit: int, offset: int):
        return []

    async def list_logs_by_target(self, target_user_id: int, *, limit: int, offset: int):
        return []

    async def get_log_by_id(self, log_id: int):
        return None


def build_action_log_service(dummy_session, user_repository, repository):
    return AdminActionLogService(
        session=dummy_session,
        user_repository=user_repository,
        admin_action_log_repository=repository,
    )


@pytest.mark.asyncio
async def test_admin_service_logs_block_unblock_grant_and_revoke(dummy_session) -> None:
    created_at = datetime(2026, 4, 5, 20, 0, tzinfo=timezone.utc)
    admin_user = make_user(
        id=1,
        telegram_id=7001,
        username="chief",
        is_admin=True,
        created_at=created_at,
    )
    target_user = make_user(
        id=2,
        telegram_id=7002,
        username="guest",
        is_admin=False,
        created_at=created_at,
    )
    user_repository = FakeUserRepository([admin_user, target_user])
    log_repository = FakeAdminActionLogRepository()
    action_log_service = build_action_log_service(dummy_session, user_repository, log_repository)
    service = AdminService(
        session=dummy_session,
        user_repository=user_repository,
        habit_repository=FakeHabitRepository(),
        feedback_repository=FakeFeedbackRepository(),
        admin_action_log_service=action_log_service,
    )

    await service.block_user(admin_user.telegram_id, target_user.id)
    await service.unblock_user(admin_user.telegram_id, target_user.id)
    await service.grant_admin(admin_user.telegram_id, target_user.id)
    await service.revoke_admin(admin_user.telegram_id, target_user.id)

    assert [log.action_type for log in log_repository.logs] == [
        "block_user",
        "unblock_user",
        "grant_admin",
        "revoke_admin",
    ]
    assert dummy_session.commit_calls == 4


@pytest.mark.asyncio
async def test_admin_service_logs_restore_deleted_habit(dummy_session) -> None:
    created_at = datetime(2026, 4, 5, 20, 0, tzinfo=timezone.utc)
    admin_user = make_user(
        id=1,
        telegram_id=8001,
        username="chief",
        is_admin=True,
        created_at=created_at,
    )
    target_user = make_user(
        id=2,
        telegram_id=8002,
        username="reader",
        created_at=created_at,
    )
    deleted_habit = make_habit(
        id=55,
        user_id=target_user.id,
        title="Чтение",
        is_deleted=True,
        is_active=False,
        user=target_user,
    )
    user_repository = FakeUserRepository([admin_user, target_user])
    log_repository = FakeAdminActionLogRepository()
    action_log_service = build_action_log_service(dummy_session, user_repository, log_repository)
    service = AdminService(
        session=dummy_session,
        user_repository=user_repository,
        habit_repository=FakeHabitRepository(deleted_habit=deleted_habit),
        feedback_repository=FakeFeedbackRepository(),
        admin_action_log_service=action_log_service,
    )

    await service.restore_deleted_habit(admin_user.telegram_id, deleted_habit.id)

    assert log_repository.logs[0].action_type == "restore_deleted_habit"
    assert log_repository.logs[0].entity_type == "habit"
    assert log_repository.logs[0].details_json == {"habit_title": "Чтение"}
    assert dummy_session.commit_calls == 1


@pytest.mark.asyncio
async def test_feedback_service_logs_reply_feedback(dummy_session) -> None:
    created_at = datetime(2026, 4, 5, 20, 0, tzinfo=timezone.utc)
    admin_user = make_user(
        id=1,
        telegram_id=9001,
        username="chief",
        is_admin=True,
        created_at=created_at,
    )
    target_user = make_user(
        id=2,
        telegram_id=9002,
        username="reader",
        created_at=created_at,
    )
    feedback = SimpleNamespace(
        id=12,
        user_id=target_user.id,
        user=target_user,
        message_text="Не приходит напоминание уже два дня",
        is_read=False,
        created_at=datetime(2026, 4, 5, 21, 0, tzinfo=timezone.utc),
        admin_reply_text=None,
        admin_replied_at=None,
    )
    user_repository = FakeUserRepository([admin_user, target_user])
    log_repository = FakeAdminActionLogRepository()
    action_log_service = build_action_log_service(dummy_session, user_repository, log_repository)
    service = FeedbackService(
        session=dummy_session,
        user_repository=user_repository,
        feedback_repository=FakeFeedbackRepository(feedback=feedback),
        admin_action_log_service=action_log_service,
    )

    await service.save_admin_reply(admin_user.telegram_id, feedback.id, "Уже всё исправили.")

    assert log_repository.logs[0].action_type == "reply_feedback"
    assert log_repository.logs[0].entity_type == "feedback"
    assert log_repository.logs[0].entity_id == 12
    assert log_repository.logs[0].details_json == {
        "feedback_reply_text": "Уже всё исправили.",
        "feedback_preview": "Не приходит напоминание уже два…",
    }
    assert dummy_session.commit_calls == 1
