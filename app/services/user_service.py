import re
from datetime import datetime, time, timezone

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User
from app.repositories.user_repository import UserRepository


LOCAL_TIME_PATTERN = re.compile(r"^\d{2}:\d{2}$")
MIN_UTC_OFFSET_MINUTES = -12 * 60
MAX_UTC_OFFSET_MINUTES = 14 * 60
MINUTES_IN_DAY = 24 * 60


class UserServiceError(Exception):
    pass


class UserTimeValidationError(UserServiceError):
    pass


class UserService:
    def __init__(self, session: AsyncSession, user_repository: UserRepository) -> None:
        self._session = session
        self._user_repository = user_repository

    async def get_or_create_user(
        self,
        *,
        telegram_id: int,
        username: str | None,
        first_name: str | None,
        last_name: str | None,
    ) -> tuple[User, bool]:
        user = await self._user_repository.get_by_telegram_id(telegram_id)

        if user is None:
            user = await self._user_repository.create(
                telegram_id=telegram_id,
                username=username,
                first_name=first_name,
                last_name=last_name,
            )
            await self._session.commit()
            await self._session.refresh(user)
            return user, True

        is_updated = False
        if user.username != username:
            user.username = username
            is_updated = True
        if user.first_name != first_name:
            user.first_name = first_name
            is_updated = True
        if user.last_name != last_name:
            user.last_name = last_name
            is_updated = True

        if is_updated:
            await self._session.commit()
            await self._session.refresh(user)

        return user, False

    async def get_by_telegram_id(self, telegram_id: int) -> User | None:
        return await self._user_repository.get_by_telegram_id(telegram_id)

    async def should_show_admin_entry_by_telegram_id(self, telegram_id: int) -> bool:
        user = await self.get_by_telegram_id(telegram_id)
        return self.should_show_admin_entry(user)

    async def set_utc_offset_from_local_time(
        self,
        user_id: int,
        raw_local_time: str,
        reference_utc_datetime: datetime | None = None,
    ) -> int:
        user = await self._user_repository.get_by_id(user_id)
        if user is None:
            raise UserTimeValidationError("Пользователь не найден.")

        local_time = self.parse_local_time(raw_local_time)
        utc_datetime = reference_utc_datetime or datetime.now(timezone.utc)
        utc_time = utc_datetime.astimezone(timezone.utc).time()

        utc_offset_minutes = self._calculate_utc_offset_minutes(local_time, utc_time)
        await self._user_repository.update_utc_offset_minutes(user, utc_offset_minutes)
        await self._session.commit()
        return utc_offset_minutes

    @staticmethod
    def parse_local_time(raw_time: str) -> time:
        normalized_time = raw_time.strip()
        if not LOCAL_TIME_PATTERN.fullmatch(normalized_time):
            raise UserTimeValidationError("Введи текущее время в формате ЧЧ:ММ.")

        hours, minutes = normalized_time.split(":")
        hour = int(hours)
        minute = int(minutes)

        if hour > 23 or minute > 59:
            raise UserTimeValidationError("Введи корректное время в формате ЧЧ:ММ.")

        return time(hour=hour, minute=minute)

    @staticmethod
    def format_utc_offset(utc_offset_minutes: int) -> str:
        sign = "+" if utc_offset_minutes >= 0 else "-"
        absolute_minutes = abs(utc_offset_minutes)
        hours, minutes = divmod(absolute_minutes, 60)
        return f"{sign}{hours:02d}:{minutes:02d}"

    @staticmethod
    def can_use_bot(user: User | None) -> bool:
        return user is None or not user.is_blocked

    @staticmethod
    def should_show_admin_entry(user: User | None) -> bool:
        return bool(user is not None and user.is_admin and not user.is_blocked)

    @staticmethod
    def _calculate_utc_offset_minutes(local_time: time, utc_time: time) -> int:
        local_total_minutes = local_time.hour * 60 + local_time.minute
        utc_total_minutes = utc_time.hour * 60 + utc_time.minute
        offset_minutes = local_total_minutes - utc_total_minutes

        while offset_minutes < MIN_UTC_OFFSET_MINUTES:
            offset_minutes += MINUTES_IN_DAY

        while offset_minutes > MAX_UTC_OFFSET_MINUTES:
            offset_minutes -= MINUTES_IN_DAY

        return offset_minutes
