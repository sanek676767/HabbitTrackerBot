"""Add feedback messages table

Revision ID: 0007_add_feedback_messages
Revises: 0006_add_progress_fields
Create Date: 2026-04-05 16:20:00

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "0007_add_feedback_messages"
down_revision: Union[str, None] = "0006_add_progress_fields"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "feedback_messages",
        sa.Column("id", sa.BigInteger(), sa.Identity(), nullable=False),
        sa.Column("user_id", sa.BigInteger(), nullable=False),
        sa.Column("message_text", sa.Text(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "is_read",
            sa.Boolean(),
            server_default=sa.text("false"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
            ondelete="CASCADE",
            name=op.f("fk_feedback_messages_user_id_users"),
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_feedback_messages")),
    )
    op.create_index(
        op.f("ix_feedback_messages_user_id"),
        "feedback_messages",
        ["user_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(op.f("ix_feedback_messages_user_id"), table_name="feedback_messages")
    op.drop_table("feedback_messages")
