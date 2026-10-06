from __future__ import annotations

from datetime import date, datetime
from enum import StrEnum
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from app.models.completed_vet_visit import CompletedVetVisit
    from app.models.diagnosis import Diagnosis
    from app.models.diary_entry import DiaryEntry
    from app.models.medication import Medication
    from app.models.user import User
    from app.models.vet_appointment import VetAppointment

from sqlalchemy import Date, DateTime, Enum, ForeignKey, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class PetSex(StrEnum):
    MALE = "male"  # самец
    FEMALE = "female"  # самка
    UNKNOWN = "unknown"  # неизвестно


class ReproductiveStatus(StrEnum):
    INTACT = "intact"  # не стерилизовано
    STERILIZED = "sterilized"  # стерилизовано
    UNKNOWN = "unknown"  # неизвестно


class Pet(Base):
    __tablename__ = "pets"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    owner_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    species: Mapped[str] = mapped_column(String(50), nullable=False)
    breed: Mapped[str | None] = mapped_column(String(100), nullable=True)
    birth_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    weight_kg: Mapped[float | None] = mapped_column(nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    # Enums are stored as plain VARCHAR (native_enum=False), so adding a value later
    # needs no Postgres ALTER TYPE migration.
    sex: Mapped[PetSex] = mapped_column(
        Enum(PetSex, native_enum=False, length=20, values_callable=lambda x: [e.value for e in x]),
        default=PetSex.UNKNOWN,
        server_default=PetSex.UNKNOWN.value,
        nullable=False,
    )
    reproductive_status: Mapped[ReproductiveStatus] = mapped_column(
        Enum(
            ReproductiveStatus,
            native_enum=False,
            length=20,
            values_callable=lambda x: [e.value for e in x],
        ),
        default=ReproductiveStatus.UNKNOWN,
        server_default=ReproductiveStatus.UNKNOWN.value,
        nullable=False,
    )
    avatar_path: Mapped[str | None] = mapped_column(String(500), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    owner: Mapped[User] = relationship("User", back_populates="pets")
    medications: Mapped[list[Medication]] = relationship(
        "Medication", back_populates="pet", cascade="all, delete-orphan"
    )
    vet_appointments: Mapped[list[VetAppointment]] = relationship(
        "VetAppointment", back_populates="pet", cascade="all, delete-orphan"
    )
    diagnoses: Mapped[list[Diagnosis]] = relationship(
        "Diagnosis", back_populates="pet", cascade="all, delete-orphan"
    )
    completed_vet_visits: Mapped[list[CompletedVetVisit]] = relationship(
        "CompletedVetVisit", back_populates="pet", cascade="all, delete-orphan"
    )
    diary_entries: Mapped[list[DiaryEntry]] = relationship(
        "DiaryEntry", back_populates="pet", cascade="all, delete-orphan"
    )
