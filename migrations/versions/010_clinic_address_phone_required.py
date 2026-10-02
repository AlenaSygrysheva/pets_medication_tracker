"""make clinics.address and clinics.phone required

Revision ID: 010
Revises: 009
Create Date: 2026-10-02
"""
from alembic import op
import sqlalchemy as sa

revision = "010"
down_revision = "009"
branch_labels = None
depends_on = None


def upgrade() -> None:
    conn = op.get_bind()
    conn.execute(sa.text("UPDATE clinics SET address = '' WHERE address IS NULL"))
    conn.execute(sa.text("UPDATE clinics SET phone = '' WHERE phone IS NULL"))
    op.alter_column("clinics", "address", existing_type=sa.String(300), nullable=False)
    op.alter_column("clinics", "phone", existing_type=sa.String(50), nullable=False)


def downgrade() -> None:
    op.alter_column("clinics", "address", existing_type=sa.String(300), nullable=True)
    op.alter_column("clinics", "phone", existing_type=sa.String(50), nullable=True)
