"""Модель ORM для привычек, напоминаний и целей прогресса."""

from datetime import date, datetime, time
from enum import Enum

from sqlalchemy import Boolean, Date, DateTime, ForeignKey, Integer, String, Time, text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, CreatedAtMixin, IdMixin, UpdatedAtMixin


class HabitFrequencyType(str, Enum):
    """Поддерживаемые режимы расписания привычек."""

    DAILY = "daily"
    INTERVAL = "interval"
    WEEKDAYS = "weekdays"


class HabitGoalType(str, Enum):
    """Поддерживаемые типы целей для привычки."""

    COMPLETIONS = "completions"
    STREAK = "streak"


class Habit(IdMixin, CreatedAtMixin, UpdatedAtMixin, Base):
    __tablename__ = "habits"

    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    title: Mapped[str] = mapped_column(String(100), nullable=False)
    frequency_type: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        default=HabitFrequencyType.DAILY.value,
        server_default=text("'daily'"),
    )
    frequency_interval: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
    )
    week_days_mask: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
    )
    start_date: Mapped[date] = mapped_column(
        Date,
        nullable=False,
        default=date.today,
        server_default=text("CURRENT_DATE"),
    )
    is_active: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=True,
        server_default=text("true"),
    )
    is_paused: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
        server_default=text("false"),
    )
    paused_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    is_deleted: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
        server_default=text("false"),
    )
    deleted_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    last_completed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    reminder_enabled: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
        server_default=text("false"),
    )
    reminder_time: Mapped[time | None] = mapped_column(
        Time(),
        nullable=True,
    )
    goal_type: Mapped[str | None] = mapped_column(
        String(32),
        nullable=True,
    )
    goal_target_value: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
    )
    goal_achieved_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    user = relationship("User", back_populates="habits")
    logs = relationship(
        "HabitLog",
        back_populates="habit",
        cascade="all, delete-orphan",
    )
