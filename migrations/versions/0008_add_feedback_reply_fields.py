"""Add feedback reply fields

Revision ID: 0008_add_feedback_reply_fields
Revises: 0007_add_feedback_messages
Create Date: 2026-04-05 18:20:00

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "0008_add_feedback_reply_fields"
down_revision: Union[str, None] = "0007_add_feedback_messages"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "feedback_messages",
        sa.Column("admin_reply_text", sa.Text(), nullable=True),
    )
    op.add_column(
        "feedback_messages",
        sa.Column("admin_replied_at", sa.DateTime(timezone=True), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("feedback_messages", "admin_replied_at")
    op.drop_column("feedback_messages", "admin_reply_text")
