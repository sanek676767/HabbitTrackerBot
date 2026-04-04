"""Add soft delete fields to habits

Revision ID: 0003_add_habit_soft_delete
Revises: 0002_add_habits
Create Date: 2026-04-04 15:20:00

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "0003_add_habit_soft_delete"
down_revision: Union[str, None] = "0002_add_habits"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "habits",
        sa.Column(
            "is_deleted",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("false"),
        ),
    )
    op.add_column(
        "habits",
        sa.Column(
            "deleted_at",
            sa.DateTime(timezone=True),
            nullable=True,
        ),
    )


def downgrade() -> None:
    op.drop_column("habits", "deleted_at")
    op.drop_column("habits", "is_deleted")
