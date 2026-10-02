"""add diagnoses table

Revision ID: 012
Revises: 011
Create Date: 2026-10-02
"""
from alembic import op
import sqlalchemy as sa

revision = "012"
down_revision = "011"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "diagnoses",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "pet_id", sa.Integer(), sa.ForeignKey("pets.id", ondelete="CASCADE"), nullable=False
        ),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("confirmed_by_vet", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("doctor_name", sa.String(200), nullable=True),
        sa.Column("comments", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_diagnoses_id", "diagnoses", ["id"])


def downgrade() -> None:
    op.drop_table("diagnoses")
