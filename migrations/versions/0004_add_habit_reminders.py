"""Add reminder fields to habits

Revision ID: 0004_add_habit_reminders
Revises: 0003_add_habit_soft_delete
Create Date: 2026-04-04 16:10:00

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "0004_add_habit_reminders"
down_revision: Union[str, None] = "0003_add_habit_soft_delete"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "habits",
        sa.Column(
            "reminder_enabled",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("false"),
        ),
    )
    op.add_column(
        "habits",
        sa.Column(
            "reminder_time",
            sa.Time(),
            nullable=True,
        ),
    )


def downgrade() -> None:
    op.drop_column("habits", "reminder_time")
    op.drop_column("habits", "reminder_enabled")
