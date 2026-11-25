from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.clock import utcnow
from app.database.base import Base


class Resource(Base):
    """quantity_available = unidades existentes (capacidade); quantity_in_use = unidades ocupadas.
    Unidades livres = quantity_available - quantity_in_use."""

    __tablename__ = "resources"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    resource_name: Mapped[str] = mapped_column(String(80), unique=True)
    quantity_available: Mapped[int] = mapped_column(Integer, default=0)
    quantity_in_use: Mapped[int] = mapped_column(Integer, default=0)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, onupdate=utcnow)


class PatientResourceRequirement(Base):
    __tablename__ = "patient_resource_requirements"
    __table_args__ = (UniqueConstraint("patient_id", "resource_id", name="uq_patient_resource"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    patient_id: Mapped[int] = mapped_column(ForeignKey("patients.id", ondelete="CASCADE"), index=True)
    resource_id: Mapped[int] = mapped_column(ForeignKey("resources.id", ondelete="CASCADE"), index=True)
    quantity: Mapped[int] = mapped_column(Integer, default=1)

    patient: Mapped["Patient"] = relationship(back_populates="resource_requirements")  # noqa: F821
    resource: Mapped[Resource] = relationship()
