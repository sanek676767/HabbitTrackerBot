"""Бизнес-логика админской рассылки пользователям через Telegram-бота."""

import logging
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import TYPE_CHECKING

from aiogram import Bot
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User
from app.repositories.user_repository import UserRepository

if TYPE_CHECKING:
    from app.services.admin_action_log_service import AdminActionLogService


logger = logging.getLogger(__name__)

BROADCAST_TYPE_TEXT = "text"
BROADCAST_TYPE_PHOTO = "photo"
BROADCAST_AUDIENCE_ACTIVE = "active"
BROADCAST_AUDIENCE_ALL = "all"
BROADCAST_LOOKBACK_DAYS = 14
BROADCAST_TEXT_MAX_LENGTH = 4096
BROADCAST_PHOTO_CAPTION_MAX_LENGTH = 1024
BROADCAST_TEXT_PREVIEW_LENGTH = 120
BROADCAST_ACTIVE_AUDIENCE_DESCRIPTION = (
    "Не заблокированные пользователи, у которых есть хотя бы одна не удалённая "
    "привычка и активность в боте за последние 14 дней."
)
BROADCAST_ALL_AUDIENCE_DESCRIPTION = (
    "Все не заблокированные пользователи, у которых есть запись в базе."
)


class BroadcastServiceError(Exception):
    pass


class BroadcastAccessDeniedError(BroadcastServiceError):
    pass


class BroadcastValidationError(BroadcastServiceError):
    pass


@dataclass(slots=True)
class BroadcastPreview:
    audience_type: str
    audience_label: str
    broadcast_type: str
    format_label: str
    text: str
    text_preview: str
    photo_file_id: str | None
    recipients_count: int
    audience_description: str

    @property
    def has_photo(self) -> bool:
        return self.photo_file_id is not None


@dataclass(slots=True)
class BroadcastResult:
    audience_type: str
    audience_label: str
    broadcast_type: str
    format_label: str
    text_preview: str
    photo_file_id: str | None
    recipients_count: int
    sent_count: int
    failed_count: int
    audience_description: str

    @property
    def has_photo(self) -> bool:
        return self.photo_file_id is not None


class BroadcastService:
    def __init__(
        self,
        session: AsyncSession,
        user_repository: UserRepository,
        admin_action_log_service: "AdminActionLogService",
    ) -> None:
        self._session = session
        self._user_repository = user_repository
        self._admin_action_log_service = admin_action_log_service

    async def prepare_broadcast(
        self,
        actor_telegram_id: int,
        *,
        audience_type: str,
        broadcast_type: str,
        text: str,
        photo_file_id: str | None = None,
    ) -> BroadcastPreview:
        await self._ensure_admin(actor_telegram_id)
        normalized_audience_type = self._normalize_audience_type(audience_type)
        normalized_type = self._normalize_broadcast_type(broadcast_type)
        normalized_text = self._normalize_text(text, broadcast_type=normalized_type)
        normalized_photo_file_id = self._normalize_photo_file_id(
            photo_file_id,
            broadcast_type=normalized_type,
        )
        recipients = await self._get_recipients(normalized_audience_type)
        return BroadcastPreview(
            audience_type=normalized_audience_type,
            audience_label=self._build_audience_label(normalized_audience_type),
            broadcast_type=normalized_type,
            format_label=self._build_format_label(normalized_type),
            text=normalized_text,
            text_preview=self._build_preview_text(normalized_text),
            photo_file_id=normalized_photo_file_id,
            recipients_count=len(recipients),
            audience_description=self._build_audience_description(
                normalized_audience_type
            ),
        )

    async def send_broadcast(
        self,
        actor_telegram_id: int,
        *,
        bot: Bot,
        audience_type: str,
        broadcast_type: str,
        text: str,
        photo_file_id: str | None = None,
    ) -> BroadcastResult:
        actor = await self._ensure_admin(actor_telegram_id)
        normalized_audience_type = self._normalize_audience_type(audience_type)
        normalized_type = self._normalize_broadcast_type(broadcast_type)
        normalized_text = self._normalize_text(text, broadcast_type=normalized_type)
        normalized_photo_file_id = self._normalize_photo_file_id(
            photo_file_id,
            broadcast_type=normalized_type,
        )
        recipients = await self._get_recipients(normalized_audience_type)

        sent_count = 0
        failed_count = 0

        for recipient in recipients:
            try:
                await self._send_to_recipient(
                    bot=bot,
                    recipient=recipient,
                    broadcast_type=normalized_type,
                    text=normalized_text,
                    photo_file_id=normalized_photo_file_id,
                )
                sent_count += 1
            except Exception:
                failed_count += 1
                logger.exception(
                    "Failed to send broadcast to telegram_id=%s",
                    recipient.telegram_id,
                )

        await self._admin_action_log_service.log_broadcast(
            actor_user_id=actor.id,
            audience_type=normalized_audience_type,
            broadcast_type=normalized_type,
            recipients_count=len(recipients),
            sent_count=sent_count,
            failed_count=failed_count,
            text_preview=self._build_preview_text(normalized_text),
            audience_summary=self._build_audience_description(normalized_audience_type),
            photo_file_id=normalized_photo_file_id,
        )
        await self._session.commit()

        return BroadcastResult(
            audience_type=normalized_audience_type,
            audience_label=self._build_audience_label(normalized_audience_type),
            broadcast_type=normalized_type,
            format_label=self._build_format_label(normalized_type),
            text_preview=self._build_preview_text(normalized_text),
            photo_file_id=normalized_photo_file_id,
            recipients_count=len(recipients),
            sent_count=sent_count,
            failed_count=failed_count,
            audience_description=self._build_audience_description(
                normalized_audience_type
            ),
        )

    async def _ensure_admin(self, actor_telegram_id: int) -> User:
        actor = await self._user_repository.get_by_telegram_id(actor_telegram_id)
        if actor is None or not actor.is_admin or actor.is_blocked:
            raise BroadcastAccessDeniedError(
                "Этот раздел доступен только администратору."
            )
        return actor

    async def _get_recipients(self, audience_type: str) -> list[User]:
        if audience_type == BROADCAST_AUDIENCE_ALL:
            return await self._user_repository.get_all_unblocked_users()

        interacted_since = datetime.now(timezone.utc) - timedelta(days=BROADCAST_LOOKBACK_DAYS)
        return await self._user_repository.get_users_for_broadcast(
            interacted_since=interacted_since
        )

    @staticmethod
    async def _send_to_recipient(
        *,
        bot: Bot,
        recipient: User,
        broadcast_type: str,
        text: str,
        photo_file_id: str | None,
    ) -> None:
        if broadcast_type == BROADCAST_TYPE_PHOTO:
            await bot.send_photo(
                chat_id=recipient.telegram_id,
                photo=photo_file_id,
                caption=text,
            )
            return

        await bot.send_message(
            chat_id=recipient.telegram_id,
            text=text,
        )

    @staticmethod
    def _normalize_broadcast_type(broadcast_type: str) -> str:
        normalized_type = broadcast_type.strip().lower()
        if normalized_type not in {BROADCAST_TYPE_TEXT, BROADCAST_TYPE_PHOTO}:
            raise BroadcastValidationError("Не удалось определить формат рассылки.")
        return normalized_type

    @staticmethod
    def _normalize_audience_type(audience_type: str) -> str:
        normalized_type = audience_type.strip().lower()
        if normalized_type not in {
            BROADCAST_AUDIENCE_ACTIVE,
            BROADCAST_AUDIENCE_ALL,
        }:
            raise BroadcastValidationError("Не удалось определить аудиторию рассылки.")
        return normalized_type

    @staticmethod
    def _normalize_text(text: str, *, broadcast_type: str) -> str:
        normalized_text = text.strip()
        if not normalized_text:
            raise BroadcastValidationError("Нужен текст рассылки.")

        max_length = (
            BROADCAST_PHOTO_CAPTION_MAX_LENGTH
            if broadcast_type == BROADCAST_TYPE_PHOTO
            else BROADCAST_TEXT_MAX_LENGTH
        )
        if len(normalized_text) > max_length:
            if broadcast_type == BROADCAST_TYPE_PHOTO:
                raise BroadcastValidationError(
                    "Подпись к картинке должна быть не длиннее 1024 символов."
                )
            raise BroadcastValidationError(
                "Текст рассылки должен быть не длиннее 4096 символов."
            )

        return normalized_text

    @staticmethod
    def _normalize_photo_file_id(
        photo_file_id: str | None,
        *,
        broadcast_type: str,
    ) -> str | None:
        normalized_photo_file_id = photo_file_id.strip() if photo_file_id else None
        if broadcast_type == BROADCAST_TYPE_PHOTO and not normalized_photo_file_id:
            raise BroadcastValidationError("Сначала загрузи картинку для рассылки.")
        return normalized_photo_file_id

    @staticmethod
    def _build_format_label(broadcast_type: str) -> str:
        if broadcast_type == BROADCAST_TYPE_PHOTO:
            return "Текст + картинка"
        return "Только текст"

    @staticmethod
    def _build_audience_label(audience_type: str) -> str:
        if audience_type == BROADCAST_AUDIENCE_ALL:
            return "Все пользователи"
        return "Активные пользователи"

    @staticmethod
    def _build_audience_description(audience_type: str) -> str:
        if audience_type == BROADCAST_AUDIENCE_ALL:
            return BROADCAST_ALL_AUDIENCE_DESCRIPTION
        return BROADCAST_ACTIVE_AUDIENCE_DESCRIPTION

    @staticmethod
    def _build_preview_text(text: str) -> str:
        normalized_text = " ".join(text.split())
        if len(normalized_text) <= BROADCAST_TEXT_PREVIEW_LENGTH:
            return normalized_text
        return f"{normalized_text[: BROADCAST_TEXT_PREVIEW_LENGTH - 1]}…"
