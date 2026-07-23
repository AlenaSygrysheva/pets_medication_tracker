"""add drugs catalog, replace medications.name with medications.drug_id

Revision ID: 007
Revises: 006
Create Date: 2026-07-25
"""
from alembic import op
import sqlalchemy as sa

revision = "007"
down_revision = "006"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "drugs",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "owner_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False
        ),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("purpose", sa.Text(), nullable=False),
        sa.Column("strength", sa.String(100), nullable=False),
        sa.Column("is_deleted", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_drugs_id", "drugs", ["id"])

    conn = op.get_bind()

    # One Drug per distinct (owner, name, dosage) combination already in use, so
    # existing courses keep a sensible catalog entry instead of losing their name.
    distinct_rows = conn.execute(sa.text("""
        SELECT DISTINCT p.owner_id, m.name, m.dosage
        FROM medications m JOIN pets p ON p.id = m.pet_id
    """)).fetchall()

    drug_ids: dict[tuple[int, str, str], int] = {}
    for owner_id, name, dosage in distinct_rows:
        result = conn.execute(
            sa.text("""
                INSERT INTO drugs (owner_id, name, purpose, strength)
                VALUES (:owner_id, :name, '', :strength)
                RETURNING id
            """),
            {"owner_id": owner_id, "name": name, "strength": dosage},
        )
        drug_ids[(owner_id, name, dosage)] = result.scalar_one()

    op.add_column("medications", sa.Column("drug_id", sa.Integer(), nullable=True))

    med_rows = conn.execute(sa.text("""
        SELECT m.id, p.owner_id, m.name, m.dosage
        FROM medications m JOIN pets p ON p.id = m.pet_id
    """)).fetchall()
    for med_id, owner_id, name, dosage in med_rows:
        conn.execute(
            sa.text("UPDATE medications SET drug_id = :drug_id WHERE id = :id"),
            {"drug_id": drug_ids[(owner_id, name, dosage)], "id": med_id},
        )

    op.alter_column("medications", "drug_id", nullable=False)
    op.create_foreign_key("fk_medications_drug_id", "medications", "drugs", ["drug_id"], ["id"])
    op.drop_column("medications", "name")


def downgrade() -> None:
    op.add_column("medications", sa.Column("name", sa.String(200), nullable=True))
    conn = op.get_bind()
    conn.execute(sa.text("""
        UPDATE medications SET name = drugs.name
        FROM drugs WHERE drugs.id = medications.drug_id
    """))
    op.alter_column("medications", "name", nullable=False)
    op.drop_constraint("fk_medications_drug_id", "medications", type_="foreignkey")
    op.drop_column("medications", "drug_id")
    op.drop_table("drugs")
