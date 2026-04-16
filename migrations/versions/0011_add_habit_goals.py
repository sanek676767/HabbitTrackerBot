"""Add habit goals

Revision ID: 0011_add_habit_goals
Revises: 0010_add_admin_action_logs
Create Date: 2026-04-10 15:00:00

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "0011_add_habit_goals"
down_revision: Union[str, None] = "0010_add_admin_action_logs"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "habits",
        sa.Column("goal_type", sa.String(length=32), nullable=True),
    )
    op.add_column(
        "habits",
        sa.Column("goal_target_value", sa.Integer(), nullable=True),
    )
    op.add_column(
        "habits",
        sa.Column("goal_achieved_at", sa.DateTime(timezone=True), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("habits", "goal_achieved_at")
    op.drop_column("habits", "goal_target_value")
    op.drop_column("habits", "goal_type")
