"""normalize legacy clinic phones, add completed_vet_visits table

Revision ID: 014
Revises: 013
Create Date: 2026-10-06
"""
import re

from alembic import op
import sqlalchemy as sa

revision = "014"
down_revision = "013"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Clinics created before the digits-only phone rule (e.g. "+7 (831) 234-36-03")
    # are brought to the current format.
    conn = op.get_bind()
    rows = conn.execute(sa.text("SELECT id, phone FROM clinics")).fetchall()
    for clinic_id, phone in rows:
        digits = re.sub(r"\D", "", phone or "")
        if digits != phone:
            conn.execute(
                sa.text("UPDATE clinics SET phone = :phone WHERE id = :id"),
                {"phone": digits, "id": clinic_id},
            )

    op.create_table(
        "completed_vet_visits",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "pet_id", sa.Integer(), sa.ForeignKey("pets.id", ondelete="CASCADE"), nullable=False
        ),
        sa.Column("clinic_name", sa.String(200), nullable=False),
        sa.Column("clinic_address", sa.String(300), nullable=True),
        sa.Column("clinic_phone", sa.String(50), nullable=True),
        sa.Column("doctor_name", sa.String(200), nullable=True),
        sa.Column("appointment_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("comments", sa.Text(), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_completed_vet_visits_id", "completed_vet_visits", ["id"])
    op.create_index("ix_completed_vet_visits_pet_id", "completed_vet_visits", ["pet_id"])


def downgrade() -> None:
    op.drop_table("completed_vet_visits")
