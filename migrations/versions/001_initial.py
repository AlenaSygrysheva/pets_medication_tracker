"""initial schema

Revision ID: 001
Revises:
Create Date: 2026-07-07
"""
import sqlalchemy as sa
from alembic import op

revision = "001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(sa.text("""
        CREATE TABLE IF NOT EXISTS users (
            id SERIAL PRIMARY KEY,
            email VARCHAR(255) NOT NULL,
            username VARCHAR(100) NOT NULL,
            hashed_password VARCHAR(255) NOT NULL,
            is_active BOOLEAN NOT NULL DEFAULT true,
            created_at TIMESTAMP WITH TIME ZONE DEFAULT now(),
            updated_at TIMESTAMP WITH TIME ZONE DEFAULT now()
        )
    """))
    op.execute(sa.text("CREATE INDEX IF NOT EXISTS ix_users_id ON users (id)"))
    op.execute(sa.text("CREATE UNIQUE INDEX IF NOT EXISTS ix_users_email ON users (email)"))
    op.execute(sa.text("CREATE UNIQUE INDEX IF NOT EXISTS ix_users_username ON users (username)"))

    op.execute(sa.text("""
        CREATE TABLE IF NOT EXISTS pets (
            id SERIAL PRIMARY KEY,
            owner_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            name VARCHAR(100) NOT NULL,
            species VARCHAR(50) NOT NULL,
            breed VARCHAR(100),
            birth_date DATE,
            weight_kg FLOAT,
            notes TEXT,
            created_at TIMESTAMP WITH TIME ZONE DEFAULT now(),
            updated_at TIMESTAMP WITH TIME ZONE DEFAULT now()
        )
    """))
    op.execute(sa.text("CREATE INDEX IF NOT EXISTS ix_pets_id ON pets (id)"))

    op.execute(sa.text("""
        CREATE TABLE IF NOT EXISTS medications (
            id SERIAL PRIMARY KEY,
            pet_id INTEGER NOT NULL REFERENCES pets(id) ON DELETE CASCADE,
            name VARCHAR(200) NOT NULL,
            dosage VARCHAR(100) NOT NULL,
            frequency_per_day INTEGER NOT NULL DEFAULT 1,
            start_date DATE NOT NULL,
            end_date DATE,
            instructions TEXT,
            is_active BOOLEAN NOT NULL DEFAULT true,
            created_at TIMESTAMP WITH TIME ZONE DEFAULT now(),
            updated_at TIMESTAMP WITH TIME ZONE DEFAULT now()
        )
    """))
    op.execute(sa.text("CREATE INDEX IF NOT EXISTS ix_medications_id ON medications (id)"))

    op.execute(sa.text("""
        DO $$ BEGIN
            CREATE TYPE dosestatus AS ENUM ('pending', 'taken', 'skipped', 'missed');
        EXCEPTION WHEN duplicate_object THEN null;
        END $$;
    """))

    op.execute(sa.text("""
        CREATE TABLE IF NOT EXISTS doses (
            id SERIAL PRIMARY KEY,
            medication_id INTEGER NOT NULL REFERENCES medications(id) ON DELETE CASCADE,
            scheduled_at TIMESTAMP WITH TIME ZONE NOT NULL,
            taken_at TIMESTAMP WITH TIME ZONE,
            status dosestatus NOT NULL DEFAULT 'pending',
            notes VARCHAR(500),
            created_at TIMESTAMP WITH TIME ZONE DEFAULT now()
        )
    """))
    op.execute(sa.text("CREATE INDEX IF NOT EXISTS ix_doses_id ON doses (id)"))


def downgrade() -> None:
    op.execute(sa.text("DROP TABLE IF EXISTS doses"))
    op.execute(sa.text("DROP TYPE IF EXISTS dosestatus"))
    op.execute(sa.text("DROP TABLE IF EXISTS medications"))
    op.execute(sa.text("DROP TABLE IF EXISTS pets"))
    op.execute(sa.text("DROP TABLE IF EXISTS users"))
