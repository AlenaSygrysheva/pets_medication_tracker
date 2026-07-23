"""add reminder_times to medications

Revision ID: 004
Revises: 003
Create Date: 2026-07-20
"""
import json

from alembic import op
import sqlalchemy as sa

revision = "004"
down_revision = "003"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("medications", sa.Column("reminder_times", sa.JSON(), nullable=True))

    conn = op.get_bind()
    meds = conn.execute(sa.text("SELECT id, frequency_per_day FROM medications")).fetchall()
    for med_id, frequency in meds:
        interval_hours = 24 // frequency
        times = [f"{min(8 + i * interval_hours, 23):02d}:00" for i in range(frequency)]
        conn.execute(
            sa.text("UPDATE medications SET reminder_times = :times WHERE id = :id"),
            {"times": json.dumps(times), "id": med_id},
        )

    op.alter_column("medications", "reminder_times", nullable=False)


def downgrade() -> None:
    op.drop_column("medications", "reminder_times")
