"""Add habits and habit logs

Revision ID: 0002_add_habits
Revises: 0001_initial_schema
Create Date: 2026-04-04 13:40:00

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "0002_add_habits"
down_revision: Union[str, None] = "0001_initial_schema"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "habits",
        sa.Column("user_id", sa.BigInteger(), nullable=False),
        sa.Column("title", sa.String(length=100), nullable=False),
        sa.Column("frequency_type", sa.String(length=32), server_default=sa.text("'daily'"), nullable=False),
        sa.Column("is_active", sa.Boolean(), server_default=sa.text("true"), nullable=False),
        sa.Column("id", sa.BigInteger(), sa.Identity(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
            name=op.f("fk_habits_user_id_users"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_habits")),
    )
    op.create_index(op.f("ix_habits_user_id"), "habits", ["user_id"], unique=False)

    op.create_table(
        "habit_logs",
        sa.Column("habit_id", sa.BigInteger(), nullable=False),
        sa.Column("completed_for_date", sa.Date(), nullable=False),
        sa.Column("id", sa.BigInteger(), sa.Identity(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(
            ["habit_id"],
            ["habits.id"],
            name=op.f("fk_habit_logs_habit_id_habits"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_habit_logs")),
        sa.UniqueConstraint(
            "habit_id",
            "completed_for_date",
            name=op.f("uq_habit_logs_habit_id_completed_for_date"),
        ),
    )
    op.create_index(op.f("ix_habit_logs_habit_id"), "habit_logs", ["habit_id"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_habit_logs_habit_id"), table_name="habit_logs")
    op.drop_table("habit_logs")

    op.drop_index(op.f("ix_habits_user_id"), table_name="habits")
    op.drop_table("habits")
