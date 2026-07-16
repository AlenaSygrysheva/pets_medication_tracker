"""add cancelled to dosestatus enum

Revision ID: 003
Revises: 002
Create Date: 2026-07-08
"""
from alembic import op

revision = "003"
down_revision = "002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("ALTER TYPE dosestatus ADD VALUE IF NOT EXISTS 'cancelled'")


def downgrade() -> None:
    pass
