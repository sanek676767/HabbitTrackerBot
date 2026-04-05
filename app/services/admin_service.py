from dataclasses import dataclass
from datetime import datetime

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User
from app.repositories.feedback_repository import FeedbackRepository
from app.repositories.habit_repository import HabitRepository
from app.repositories.user_repository import UserRepository


USER_SEARCH_LIMIT = 20


class AdminServiceError(Exception):
    pass


class AdminAccessDeniedError(AdminServiceError):
    pass


class AdminUserNotFoundError(AdminServiceError):
    pass


class AdminHabitNotFoundError(AdminServiceError):
    pass


class AdminActionValidationError(AdminServiceError):
    pass


@dataclass(slots=True)
class AdminDashboardData:
    total_users_count: int
    admin_users_count: int
    blocked_users_count: int
    deleted_habits_count: int
    unread_feedback_count: int


@dataclass(slots=True)
class AdminUserListItem:
    id: int
    telegram_id: int
    username: str | None
    full_name: str | None
    is_admin: bool
    is_blocked: bool


@dataclass(slots=True)
class AdminUserCard:
    id: int
    telegram_id: int
    username: str | None
    full_name: str | None
    is_admin: bool
    is_blocked: bool
    active_habits_count: int
    archived_habits_count: int
    deleted_habits_count: int
    created_at: datetime
    last_completed_habit_title: str | None
    last_completed_at: datetime | None


@dataclass(slots=True)
class DeletedHabitListItem:
    id: int
    title: str
    deleted_at: datetime | None


class AdminService:
    def __init__(
        self,
        session: AsyncSession,
        user_repository: UserRepository,
        habit_repository: HabitRepository,
        feedback_repository: FeedbackRepository,
    ) -> None:
        self._session = session
        self._user_repository = user_repository
        self._habit_repository = habit_repository
        self._feedback_repository = feedback_repository

    async def get_dashboard(self, actor_telegram_id: int) -> AdminDashboardData:
        await self._get_admin_actor(actor_telegram_id)
        return AdminDashboardData(
            total_users_count=await self._user_repository.count_users(),
            admin_users_count=await self._user_repository.count_admin_users(),
            blocked_users_count=await self._user_repository.count_blocked_users(),
            deleted_habits_count=await self._habit_repository.count_deleted_habits(),
            unread_feedback_count=await self._feedback_repository.count_unread_feedback(),
        )

    async def search_users(
        self,
        actor_telegram_id: int,
        query: str,
    ) -> list[AdminUserListItem]:
        await self._get_admin_actor(actor_telegram_id)
        users = await self._user_repository.search_users(
            query,
            limit=USER_SEARCH_LIMIT,
        )
        return [self._build_user_list_item(user) for user in users]

    async def list_users(self, actor_telegram_id: int) -> list[AdminUserListItem]:
        return await self.search_users(actor_telegram_id, "")

    async def get_user_card(
        self,
        actor_telegram_id: int,
        target_user_id: int,
    ) -> AdminUserCard:
        await self._get_admin_actor(actor_telegram_id)
        target_user = await self._get_target_user(target_user_id)
        return await self._build_user_card(target_user)

    async def block_user(
        self,
        actor_telegram_id: int,
        target_user_id: int,
    ) -> AdminUserCard:
        actor = await self._get_admin_actor(actor_telegram_id)
        target_user = await self._get_target_user(target_user_id)
        self._ensure_can_change_block_state(actor, target_user)

        await self._user_repository.update_is_blocked(target_user, True)
        await self._session.commit()
        return await self._build_user_card(target_user)

    async def unblock_user(
        self,
        actor_telegram_id: int,
        target_user_id: int,
    ) -> AdminUserCard:
        await self._get_admin_actor(actor_telegram_id)
        target_user = await self._get_target_user(target_user_id)

        await self._user_repository.update_is_blocked(target_user, False)
        await self._session.commit()
        return await self._build_user_card(target_user)

    async def grant_admin(
        self,
        actor_telegram_id: int,
        target_user_id: int,
    ) -> AdminUserCard:
        await self._get_admin_actor(actor_telegram_id)
        target_user = await self._get_target_user(target_user_id)

        await self._user_repository.update_is_admin(target_user, True)
        await self._session.commit()
        return await self._build_user_card(target_user)

    async def revoke_admin(
        self,
        actor_telegram_id: int,
        target_user_id: int,
    ) -> AdminUserCard:
        actor = await self._get_admin_actor(actor_telegram_id)
        target_user = await self._get_target_user(target_user_id)
        self._ensure_can_revoke_admin(actor, target_user)

        await self._user_repository.update_is_admin(target_user, False)
        await self._session.commit()
        return await self._build_user_card(target_user)

    async def get_deleted_habits(
        self,
        actor_telegram_id: int,
        target_user_id: int,
    ) -> list[DeletedHabitListItem]:
        await self._get_admin_actor(actor_telegram_id)
        await self._get_target_user(target_user_id)
        habits = await self._habit_repository.get_deleted_habits_by_user(target_user_id)
        return [
            DeletedHabitListItem(
                id=habit.id,
                title=habit.title,
                deleted_at=habit.deleted_at,
            )
            for habit in habits
        ]

    async def restore_deleted_habit(
        self,
        actor_telegram_id: int,
        habit_id: int,
    ) -> DeletedHabitListItem:
        await self._get_admin_actor(actor_telegram_id)
        habit = await self._habit_repository.get_habit_by_id(habit_id)
        if habit is None or not habit.is_deleted:
            raise AdminHabitNotFoundError("Удалённая привычка не найдена.")

        await self._habit_repository.restore_soft_deleted_habit(habit)
        await self._session.commit()
        return DeletedHabitListItem(
            id=habit.id,
            title=habit.title,
            deleted_at=habit.deleted_at,
        )

    async def _get_admin_actor(self, actor_telegram_id: int) -> User:
        actor = await self._user_repository.get_by_telegram_id(actor_telegram_id)
        if actor is None or not actor.is_admin or actor.is_blocked:
            raise AdminAccessDeniedError("Доступ к admin panel закрыт.")
        return actor

    async def _get_target_user(self, target_user_id: int) -> User:
        user = await self._user_repository.get_by_id(target_user_id)
        if user is None:
            raise AdminUserNotFoundError("Пользователь не найден.")
        return user

    async def _build_user_card(self, user: User) -> AdminUserCard:
        last_completed_habits = await self._habit_repository.get_last_completed_habits_by_user(
            user.id,
            limit=1,
        )
        last_completed_habit = last_completed_habits[0] if last_completed_habits else None
        return AdminUserCard(
            id=user.id,
            telegram_id=user.telegram_id,
            username=user.username,
            full_name=self._build_full_name(user.first_name, user.last_name),
            is_admin=user.is_admin,
            is_blocked=user.is_blocked,
            active_habits_count=await self._habit_repository.count_active_habits(user.id),
            archived_habits_count=await self._habit_repository.count_archived_habits(user.id),
            deleted_habits_count=await self._habit_repository.count_deleted_habits(user.id),
            created_at=user.created_at,
            last_completed_habit_title=(
                last_completed_habit.title if last_completed_habit is not None else None
            ),
            last_completed_at=(
                last_completed_habit.last_completed_at if last_completed_habit is not None else None
            ),
        )

    @staticmethod
    def _build_user_list_item(user: User) -> AdminUserListItem:
        return AdminUserListItem(
            id=user.id,
            telegram_id=user.telegram_id,
            username=user.username,
            full_name=AdminService._build_full_name(user.first_name, user.last_name),
            is_admin=user.is_admin,
            is_blocked=user.is_blocked,
        )

    @staticmethod
    def _build_full_name(first_name: str | None, last_name: str | None) -> str | None:
        full_name = " ".join(part for part in [first_name, last_name] if part)
        return full_name or None

    @staticmethod
    def _ensure_can_change_block_state(actor: User, target_user: User) -> None:
        if actor.id == target_user.id:
            raise AdminActionValidationError("Нельзя блокировать самого себя.")

    @staticmethod
    def _ensure_can_revoke_admin(actor: User, target_user: User) -> None:
        if actor.id == target_user.id:
            raise AdminActionValidationError("Нельзя снять admin у самого себя.")
