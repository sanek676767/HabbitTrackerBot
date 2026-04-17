"""Модель ORM для ежедневных отметок выполнения привычек."""

from datetime import date

from sqlalchemy import Date, ForeignKey, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, CreatedAtMixin, IdMixin


class HabitLog(IdMixin, CreatedAtMixin, Base):
    __tablename__ = "habit_logs"
    __table_args__ = (
        UniqueConstraint(
            "habit_id",
            "completed_for_date",
            name="uq_habit_logs_habit_id_completed_for_date",
        ),
    )

    habit_id: Mapped[int] = mapped_column(
        ForeignKey("habits.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    completed_for_date: Mapped[date] = mapped_column(Date, nullable=False)

    habit = relationship("Habit", back_populates="logs")
