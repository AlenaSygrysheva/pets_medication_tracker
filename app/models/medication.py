from __future__ import annotations

from datetime import date, datetime
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from app.models.dose import Dose
    from app.models.drug import Drug
    from app.models.pet import Pet

from sqlalchemy import JSON, Date, DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class Medication(Base):
    __tablename__ = "medications"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    pet_id: Mapped[int] = mapped_column(ForeignKey("pets.id", ondelete="CASCADE"), nullable=False)
    drug_id: Mapped[int] = mapped_column(ForeignKey("drugs.id"), nullable=False)
    dosage: Mapped[str] = mapped_column(String(100), nullable=False)
    frequency_per_day: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    reminder_times: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)
    start_date: Mapped[date] = mapped_column(Date, nullable=False)
    end_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    instructions: Mapped[str | None] = mapped_column(Text, nullable=True)
    is_active: Mapped[bool] = mapped_column(default=True)
    is_deleted: Mapped[bool] = mapped_column(default=False, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    pet: Mapped[Pet] = relationship("Pet", back_populates="medications")
    drug: Mapped[Drug] = relationship("Drug", back_populates="medications")
    doses: Mapped[list[Dose]] = relationship("Dose", back_populates="medication", cascade="all, delete-orphan")
