"""add diary_entries table

Revision ID: 015
Revises: 014
Create Date: 2026-10-06
"""
from alembic import op
import sqlalchemy as sa

revision = "015"
down_revision = "014"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "diary_entries",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "pet_id", sa.Integer(), sa.ForeignKey("pets.id", ondelete="CASCADE"), nullable=False
        ),
        sa.Column("text", sa.String(500), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_diary_entries_id", "diary_entries", ["id"])
    op.create_index("ix_diary_entries_pet_id", "diary_entries", ["pet_id"])


def downgrade() -> None:
    op.drop_table("diary_entries")
