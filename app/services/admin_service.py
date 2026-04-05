from dataclasses import dataclass
from datetime import datetime, time

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User
from app.repositories.feedback_repository import FeedbackRepository
from app.repositories.habit_repository import HabitRepository
from app.repositories.user_repository import UserRepository


USER_SEARCH_LIMIT = 20
ADMIN_PAGE_SIZE = 6


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
class AdminPagination:
    page: int
    total_items: int
    total_pages: int
    has_prev: bool
    has_next: bool


@dataclass(slots=True)
class AdminUsersPage:
    items: list["AdminUserListItem"]
    pagination: AdminPagination


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
class AdminHabitListItem:
    id: int
    title: str
    owner_user_id: int
    owner_telegram_id: int
    owner_username: str | None
    reminder_enabled: bool
    reminder_time: time | None
    last_completed_at: datetime | None
    deleted_at: datetime | None


@dataclass(slots=True)
class AdminHabitListPage:
    list_type: str
    owner_user_id: int | None
    owner_telegram_id: int | None
    owner_display_name: str
    items: list[AdminHabitListItem]
    pagination: AdminPagination


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
        users = await self._user_repository.search_users(query, limit=USER_SEARCH_LIMIT)
        return [self._build_user_list_item(user) for user in users]

    async def list_users_page(
        self,
        actor_telegram_id: int,
        page: int,
        *,
        page_size: int = ADMIN_PAGE_SIZE,
    ) -> AdminUsersPage:
        await self._get_admin_actor(actor_telegram_id)
        total_items = await self._user_repository.count_search_users("")
        pagination = self._build_pagination(
            requested_page=page,
            total_items=total_items,
            page_size=page_size,
        )
        users = await self._user_repository.search_users(
            "",
            limit=page_size,
            offset=(pagination.page - 1) * page_size,
        )
        return AdminUsersPage(
            items=[self._build_user_list_item(user) for user in users],
            pagination=pagination,
        )

    async def list_users(self, actor_telegram_id: int) -> list[AdminUserListItem]:
        page = await self.list_users_page(actor_telegram_id, page=1, page_size=USER_SEARCH_LIMIT)
        return page.items

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
    ) -> list[AdminHabitListItem]:
        page = await self.get_user_habits_page(
            actor_telegram_id,
            target_user_id,
            list_type="deleted",
            page=1,
            page_size=USER_SEARCH_LIMIT,
        )
        return page.items

    async def get_user_habits_page(
        self,
        actor_telegram_id: int,
        target_user_id: int,
        *,
        list_type: str,
        page: int,
        page_size: int = ADMIN_PAGE_SIZE,
    ) -> AdminHabitListPage:
        await self._get_admin_actor(actor_telegram_id)
        target_user = await self._get_target_user(target_user_id)

        if list_type == "active":
            total_items = await self._habit_repository.count_active_habits(target_user.id)
        elif list_type == "archived":
            total_items = await self._habit_repository.count_archived_habits(target_user.id)
        elif list_type == "deleted":
            total_items = await self._habit_repository.count_deleted_habits(target_user.id)
        else:
            raise AdminActionValidationError("Не удалось открыть этот список привычек.")

        pagination = self._build_pagination(
            requested_page=page,
            total_items=total_items,
            page_size=page_size,
        )
        offset = (pagination.page - 1) * page_size

        if list_type == "active":
            habits = await self._habit_repository.get_active_habits_by_user(
                target_user.id,
                limit=page_size,
                offset=offset,
            )
        elif list_type == "archived":
            habits = await self._habit_repository.get_archived_habits_by_user(
                target_user.id,
                limit=page_size,
                offset=offset,
            )
        else:
            habits = await self._habit_repository.get_deleted_habits_by_user(
                target_user.id,
                limit=page_size,
                offset=offset,
            )

        return AdminHabitListPage(
            list_type=list_type,
            owner_user_id=target_user.id,
            owner_telegram_id=target_user.telegram_id,
            owner_display_name=self._build_owner_display(target_user),
            items=[self._build_habit_list_item(habit, target_user) for habit in habits],
            pagination=pagination,
        )

    async def get_global_deleted_habits_page(
        self,
        actor_telegram_id: int,
        *,
        page: int,
        page_size: int = ADMIN_PAGE_SIZE,
    ) -> AdminHabitListPage:
        await self._get_admin_actor(actor_telegram_id)
        total_items = await self._habit_repository.count_deleted_habits()
        pagination = self._build_pagination(
            requested_page=page,
            total_items=total_items,
            page_size=page_size,
        )
        habits = await self._habit_repository.get_deleted_habits(
            limit=page_size,
            offset=(pagination.page - 1) * page_size,
        )
        return AdminHabitListPage(
            list_type="global_deleted",
            owner_user_id=None,
            owner_telegram_id=None,
            owner_display_name="Все пользователи",
            items=[
                self._build_habit_list_item(habit, habit.user)
                for habit in habits
                if habit.user is not None
            ],
            pagination=pagination,
        )

    async def get_deleted_habit(
        self,
        actor_telegram_id: int,
        habit_id: int,
    ) -> AdminHabitListItem:
        await self._get_admin_actor(actor_telegram_id)
        habit = await self._habit_repository.get_habit_by_id(habit_id)
        if habit is None or not habit.is_deleted or habit.user is None:
            raise AdminHabitNotFoundError("Удалённая привычка не найдена.")
        return self._build_habit_list_item(habit, habit.user)

    async def restore_deleted_habit(
        self,
        actor_telegram_id: int,
        habit_id: int,
    ) -> AdminHabitListItem:
        await self._get_admin_actor(actor_telegram_id)
        habit = await self._habit_repository.get_habit_by_id(habit_id)
        if habit is None or not habit.is_deleted or habit.user is None:
            raise AdminHabitNotFoundError("Удалённая привычка не найдена.")

        await self._habit_repository.restore_soft_deleted_habit(habit)
        await self._session.commit()
        return AdminHabitListItem(
            id=habit.id,
            title=habit.title,
            owner_user_id=habit.user.id,
            owner_telegram_id=habit.user.telegram_id,
            owner_username=habit.user.username,
            reminder_enabled=habit.reminder_enabled,
            reminder_time=habit.reminder_time,
            last_completed_at=habit.last_completed_at,
            deleted_at=habit.deleted_at,
        )

    async def _get_admin_actor(self, actor_telegram_id: int) -> User:
        actor = await self._user_repository.get_by_telegram_id(actor_telegram_id)
        if actor is None or not actor.is_admin or actor.is_blocked:
            raise AdminAccessDeniedError("Этот раздел доступен только администратору.")
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
    def _build_habit_list_item(habit, owner: User) -> AdminHabitListItem:
        return AdminHabitListItem(
            id=habit.id,
            title=habit.title,
            owner_user_id=owner.id,
            owner_telegram_id=owner.telegram_id,
            owner_username=owner.username,
            reminder_enabled=habit.reminder_enabled,
            reminder_time=habit.reminder_time,
            last_completed_at=habit.last_completed_at,
            deleted_at=habit.deleted_at,
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
    def _build_owner_display(user: User) -> str:
        if user.username:
            return f"@{user.username}"
        full_name = AdminService._build_full_name(user.first_name, user.last_name)
        if full_name is not None:
            return full_name
        return str(user.telegram_id)

    @staticmethod
    def _build_pagination(
        *,
        requested_page: int,
        total_items: int,
        page_size: int,
    ) -> AdminPagination:
        total_pages = max(1, (total_items + page_size - 1) // page_size)
        page = min(max(requested_page, 1), total_pages)
        return AdminPagination(
            page=page,
            total_items=total_items,
            total_pages=total_pages,
            has_prev=page > 1,
            has_next=page < total_pages,
        )

    @staticmethod
    def _ensure_can_change_block_state(actor: User, target_user: User) -> None:
        if actor.id == target_user.id:
            raise AdminActionValidationError("Нельзя блокировать самого себя.")

    @staticmethod
    def _ensure_can_revoke_admin(actor: User, target_user: User) -> None:
        if actor.id == target_user.id:
            raise AdminActionValidationError("Нельзя снять права администратора у самого себя.")
