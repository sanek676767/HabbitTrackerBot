"""Add utc offset to users

Revision ID: 0005_add_user_utc_offset
Revises: 0004_add_habit_reminders
Create Date: 2026-04-04 18:05:00

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "0005_add_user_utc_offset"
down_revision: Union[str, None] = "0004_add_habit_reminders"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "users",
        sa.Column(
            "utc_offset_minutes",
            sa.Integer(),
            nullable=True,
        ),
    )


def downgrade() -> None:
    op.drop_column("users", "utc_offset_minutes")
