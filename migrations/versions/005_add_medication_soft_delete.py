"""add is_deleted to medications for soft delete

Revision ID: 005
Revises: 004
Create Date: 2026-07-23
"""
from alembic import op
import sqlalchemy as sa

revision = "005"
down_revision = "004"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "medications",
        sa.Column("is_deleted", sa.Boolean(), nullable=False, server_default=sa.false()),
    )


def downgrade() -> None:
    op.drop_column("medications", "is_deleted")
