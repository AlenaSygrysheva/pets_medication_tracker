from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from app.models.pet import Pet

from sqlalchemy import DateTime, ForeignKey, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base

DIARY_TEXT_MAX_LENGTH = 500


class DiaryEntry(Base):
    """A note in the pet's condition diary ("дневник состояния")."""

    __tablename__ = "diary_entries"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    pet_id: Mapped[int] = mapped_column(
        ForeignKey("pets.id", ondelete="CASCADE"), nullable=False, index=True
    )
    text: Mapped[str] = mapped_column(String(DIARY_TEXT_MAX_LENGTH), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    pet: Mapped[Pet] = relationship("Pet", back_populates="diary_entries")
