"""add password reset token fields to users

Revision ID: 006
Revises: 005
Create Date: 2026-07-24
"""
from alembic import op
import sqlalchemy as sa

revision = "006"
down_revision = "005"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("users", sa.Column("reset_token_hash", sa.String(64), nullable=True))
    op.add_column(
        "users", sa.Column("reset_token_expires_at", sa.DateTime(timezone=True), nullable=True)
    )
    op.create_index("ix_users_reset_token_hash", "users", ["reset_token_hash"])


def downgrade() -> None:
    op.drop_index("ix_users_reset_token_hash", table_name="users")
    op.drop_column("users", "reset_token_expires_at")
    op.drop_column("users", "reset_token_hash")
