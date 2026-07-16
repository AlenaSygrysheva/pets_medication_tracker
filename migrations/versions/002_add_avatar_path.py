"""add avatar_path to pets

Revision ID: 002
Revises: 001
Create Date: 2026-07-07
"""
from alembic import op
import sqlalchemy as sa

revision = "002"
down_revision = "001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("pets", sa.Column("avatar_path", sa.String(500), nullable=True))


def downgrade() -> None:
    op.drop_column("pets", "avatar_path")
