import pytest

from app.services.broadcast_service import (
    BROADCAST_AUDIENCE_ACTIVE,
    BROADCAST_AUDIENCE_ALL,
    BROADCAST_TYPE_PHOTO,
    BROADCAST_TYPE_TEXT,
    BroadcastService,
    BroadcastValidationError,
)
from tests.helpers import make_user


class FakeUserRepository:
    def __init__(self, admin_user, *, active_recipients, all_recipients=None) -> None:
        self.admin_user = admin_user
        self.active_recipients = active_recipients
        self.all_recipients = all_recipients or active_recipients
        self.active_calls = 0
        self.all_calls = 0

    async def get_by_telegram_id(self, telegram_id: int):
        if telegram_id == self.admin_user.telegram_id:
            return self.admin_user
        return None

    async def get_users_for_broadcast(self, *, interacted_since):
        self.active_calls += 1
        return list(self.active_recipients)

    async def get_all_unblocked_users(self):
        self.all_calls += 1
        return list(self.all_recipients)


class FakeAdminActionLogService:
    def __init__(self) -> None:
        self.calls: list[dict[str, object]] = []

    async def log_broadcast(self, **payload) -> None:
        self.calls.append(payload)


class FakeBot:
    def __init__(self, *, fail_chat_ids=None) -> None:
        self.fail_chat_ids = set(fail_chat_ids or [])
        self.send_message_calls: list[dict[str, object]] = []
        self.send_photo_calls: list[dict[str, object]] = []

    async def send_message(self, **payload) -> None:
        self.send_message_calls.append(payload)
        if payload["chat_id"] in self.fail_chat_ids:
            raise RuntimeError("delivery failed")

    async def send_photo(self, **payload) -> None:
        self.send_photo_calls.append(payload)
        if payload["chat_id"] in self.fail_chat_ids:
            raise RuntimeError("delivery failed")


@pytest.mark.asyncio
async def test_send_text_broadcast_counts_partial_failures_and_logs(dummy_session) -> None:
    admin_user = make_user(id=1, telegram_id=7001, is_admin=True)
    first_user = make_user(id=2, telegram_id=7002, username="reader")
    second_user = make_user(id=3, telegram_id=7003, username="runner")
    user_repository = FakeUserRepository(
        admin_user,
        active_recipients=[first_user, second_user],
    )
    action_log_service = FakeAdminActionLogService()
    bot = FakeBot(fail_chat_ids={second_user.telegram_id})
    service = BroadcastService(
        session=dummy_session,
        user_repository=user_repository,
        admin_action_log_service=action_log_service,
    )

    result = await service.send_broadcast(
        admin_user.telegram_id,
        bot=bot,
        audience_type=BROADCAST_AUDIENCE_ACTIVE,
        broadcast_type=BROADCAST_TYPE_TEXT,
        text="  Всем привет!  ",
    )

    assert user_repository.active_calls == 1
    assert user_repository.all_calls == 0
    assert result.audience_type == BROADCAST_AUDIENCE_ACTIVE
    assert result.audience_label == "Активные пользователи"
    assert result.broadcast_type == BROADCAST_TYPE_TEXT
    assert result.recipients_count == 2
    assert result.sent_count == 1
    assert result.failed_count == 1
    assert bot.send_message_calls == [
        {"chat_id": 7002, "text": "Всем привет!"},
        {"chat_id": 7003, "text": "Всем привет!"},
    ]
    assert action_log_service.calls == [
        {
            "actor_user_id": admin_user.id,
            "audience_type": "active",
            "broadcast_type": "text",
            "recipients_count": 2,
            "sent_count": 1,
            "failed_count": 1,
            "text_preview": "Всем привет!",
            "audience_summary": (
                "Не заблокированные пользователи, у которых есть хотя бы одна "
                "не удалённая привычка и активность в боте за последние 14 дней."
            ),
            "photo_file_id": None,
        }
    ]
    assert dummy_session.commit_calls == 1


@pytest.mark.asyncio
async def test_send_photo_broadcast_to_all_users_uses_caption_and_single_photo(
    dummy_session,
) -> None:
    admin_user = make_user(id=1, telegram_id=7101, is_admin=True)
    active_recipient = make_user(id=2, telegram_id=7102, username="reader")
    inactive_recipient = make_user(id=3, telegram_id=7103, username="sleeper")
    user_repository = FakeUserRepository(
        admin_user,
        active_recipients=[active_recipient],
        all_recipients=[active_recipient, inactive_recipient],
    )
    action_log_service = FakeAdminActionLogService()
    bot = FakeBot()
    service = BroadcastService(
        session=dummy_session,
        user_repository=user_repository,
        admin_action_log_service=action_log_service,
    )

    result = await service.send_broadcast(
        admin_user.telegram_id,
        bot=bot,
        audience_type=BROADCAST_AUDIENCE_ALL,
        broadcast_type=BROADCAST_TYPE_PHOTO,
        text="Новая карточка недели",
        photo_file_id="photo-file-id-1",
    )

    assert user_repository.active_calls == 0
    assert user_repository.all_calls == 1
    assert result.audience_type == BROADCAST_AUDIENCE_ALL
    assert result.audience_label == "Все пользователи"
    assert result.broadcast_type == BROADCAST_TYPE_PHOTO
    assert result.sent_count == 2
    assert result.failed_count == 0
    assert bot.send_photo_calls == [
        {
            "chat_id": 7102,
            "photo": "photo-file-id-1",
            "caption": "Новая карточка недели",
        },
        {
            "chat_id": 7103,
            "photo": "photo-file-id-1",
            "caption": "Новая карточка недели",
        },
    ]


@pytest.mark.asyncio
async def test_prepare_photo_broadcast_requires_photo(dummy_session) -> None:
    admin_user = make_user(id=1, telegram_id=7201, is_admin=True)
    service = BroadcastService(
        session=dummy_session,
        user_repository=FakeUserRepository(
            admin_user,
            active_recipients=[],
        ),
        admin_action_log_service=FakeAdminActionLogService(),
    )

    with pytest.raises(BroadcastValidationError):
        await service.prepare_broadcast(
            admin_user.telegram_id,
            audience_type=BROADCAST_AUDIENCE_ACTIVE,
            broadcast_type=BROADCAST_TYPE_PHOTO,
            text="Подпись",
            photo_file_id=None,
        )
