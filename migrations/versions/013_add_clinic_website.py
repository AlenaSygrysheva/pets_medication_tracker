"""add clinics.website

Revision ID: 013
Revises: 012
Create Date: 2026-10-02
"""
from alembic import op
import sqlalchemy as sa

revision = "013"
down_revision = "012"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("clinics", sa.Column("website", sa.String(300), nullable=True))


def downgrade() -> None:
    op.drop_column("clinics", "website")
