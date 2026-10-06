from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from app.models.pet import Pet

from sqlalchemy import DateTime, ForeignKey, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class CompletedVetVisit(Base):
    """A vet appointment marked as "приём состоялся".

    The original VetAppointment row is deleted on completion, so the clinic
    details are copied here as a snapshot — the history stays intact even if
    the clinic is later edited or removed from the catalog.
    """

    __tablename__ = "completed_vet_visits"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    pet_id: Mapped[int] = mapped_column(
        ForeignKey("pets.id", ondelete="CASCADE"), nullable=False, index=True
    )
    clinic_name: Mapped[str] = mapped_column(String(200), nullable=False)
    clinic_address: Mapped[str | None] = mapped_column(String(300), nullable=True)
    clinic_phone: Mapped[str | None] = mapped_column(String(50), nullable=True)
    doctor_name: Mapped[str | None] = mapped_column(String(200), nullable=True)
    appointment_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    comments: Mapped[str | None] = mapped_column(Text, nullable=True)
    completed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    pet: Mapped[Pet] = relationship("Pet", back_populates="completed_vet_visits")
