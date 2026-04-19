from datetime import datetime, timezone
from types import SimpleNamespace

import pytest

from app.services.admin_action_log_service import AdminActionLogService
from tests.helpers import make_user


class FakeUserRepository:
    def __init__(self, users) -> None:
        self.users_by_id = {user.id: user for user in users}
        self.users_by_telegram_id = {user.telegram_id: user for user in users}

    async def get_by_telegram_id(self, telegram_id: int):
        return self.users_by_telegram_id.get(telegram_id)


class FakeAdminActionLogRepository:
    def __init__(self, users_by_id) -> None:
        self.users_by_id = users_by_id
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
            created_at=datetime(2026, 4, 5, 23, 45, tzinfo=timezone.utc),
            actor_user=self.users_by_id.get(actor_user_id),
            target_user=self.users_by_id.get(target_user_id),
        )
        self.logs.append(log)
        return log

    async def list_logs(self, *, limit: int, offset: int):
        return list(reversed(self.logs))[offset : offset + limit]

    async def list_logs_by_actor(self, actor_user_id: int, *, limit: int, offset: int):
        filtered = [log for log in reversed(self.logs) if log.actor_user_id == actor_user_id]
        return filtered[offset : offset + limit]

    async def list_logs_by_target(self, target_user_id: int, *, limit: int, offset: int):
        filtered = [log for log in reversed(self.logs) if log.target_user_id == target_user_id]
        return filtered[offset : offset + limit]

    async def get_log_by_id(self, log_id: int):
        for log in self.logs:
            if log.id == log_id:
                return log
        return None

    async def count_logs(self) -> int:
        return len(self.logs)


def build_service():
    admin_user = make_user(id=1, telegram_id=5001, username="boss", is_admin=True)
    target_user = make_user(id=2, telegram_id=5002, username="reader")
    user_repository = FakeUserRepository([admin_user, target_user])
    repository = FakeAdminActionLogRepository(
        {
            admin_user.id: admin_user,
            target_user.id: target_user,
        }
    )
    service = AdminActionLogService(
        session=None,
        user_repository=user_repository,
        admin_action_log_repository=repository,
    )
    return service, repository, admin_user, target_user


@pytest.mark.asyncio
async def test_get_logs_page_returns_human_readable_items() -> None:
    service, repository, admin_user, target_user = build_service()
    await repository.create_log(
        actor_user_id=admin_user.id,
        target_user_id=target_user.id,
        action_type="restore_deleted_habit",
        entity_type="habit",
        entity_id=15,
        details_json={"habit_title": "Чтение"},
    )

    page = await service.get_logs_page(admin_user.telegram_id, page=1)

    assert page.pagination.total_items == 1
    assert page.items[0].action_text == "восстановил удалённую привычку"
    assert page.items[0].entity_text == "привычка «Чтение»"
    assert page.items[0].summary_text == "@boss • восстановил удалённую привычку • 05.04 23:45"


@pytest.mark.asyncio
async def test_get_log_card_formats_details_for_feedback_reply() -> None:
    service, repository, admin_user, target_user = build_service()
    await repository.create_log(
        actor_user_id=admin_user.id,
        target_user_id=target_user.id,
        action_type="reply_feedback",
        entity_type="feedback",
        entity_id=8,
        details_json={
            "feedback_preview": "Не приходит напоминание",
            "feedback_reply_text": "Проверили и исправили.",
        },
    )

    card = await service.get_log_card(admin_user.telegram_id, 1)

    assert card.actor_display_name == "@boss"
    assert card.target_display_name == "@reader"
    assert card.action_text == "ответил на обращение"
    assert card.entity_text == "обращение #8"
    assert [(item.label, item.value) for item in card.details] == [
        ("Текст обращения", "Не приходит напоминание"),
        ("Текст ответа", "Проверили и исправили."),
    ]


@pytest.mark.asyncio
async def test_get_log_card_formats_details_for_broadcast() -> None:
    service, repository, admin_user, _ = build_service()
    await repository.create_log(
        actor_user_id=admin_user.id,
        action_type="send_broadcast",
        entity_type="broadcast",
        details_json={
            "broadcast_type": "photo",
            "audience_type": "all",
            "audience_summary": "Все не заблокированные пользователи, у которых есть запись в базе.",
            "recipients_count": 5,
            "sent_count": 4,
            "failed_count": 1,
            "text_preview": "Новая неделя, новый ритм",
            "photo_file_id": "photo-file-id-1",
        },
    )

    card = await service.get_log_card(admin_user.telegram_id, 1)

    assert card.action_text == "отправил рассылку"
    assert card.entity_text == "рассылка"
    assert [(item.label, item.value) for item in card.details] == [
        ("Тип", "photo"),
        ("Тип аудитории", "all"),
        ("Аудитория", "Все не заблокированные пользователи, у которых есть запись в базе."),
        ("Получателей", "5"),
        ("Отправлено", "4"),
        ("Не доставлено", "1"),
        ("Превью текста", "Новая неделя, новый ритм"),
        ("File ID картинки", "photo-file-id-1"),
    ]
