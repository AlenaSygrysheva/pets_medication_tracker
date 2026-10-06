"""add pets.reproductive_status

Revision ID: 016
Revises: 015
Create Date: 2026-10-06
"""
from alembic import op
import sqlalchemy as sa

revision = "016"
down_revision = "015"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Existing pets get "unknown" via the server default.
    op.add_column(
        "pets",
        sa.Column(
            "reproductive_status", sa.String(20), nullable=False, server_default="unknown"
        ),
    )


def downgrade() -> None:
    op.drop_column("pets", "reproductive_status")
