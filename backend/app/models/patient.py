from datetime import datetime
from typing import Optional

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.clock import utcnow
from app.database.base import Base

PATIENT_STATUSES = ("waiting", "in_service", "attended", "left")


class Patient(Base):
    __tablename__ = "patients"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    patient_code: Mapped[str] = mapped_column(String(32), unique=True, index=True)
    age: Mapped[int] = mapped_column(Integer)
    sex: Mapped[Optional[str]] = mapped_column(String(1), nullable=True)
    status: Mapped[str] = mapped_column(String(20), default="waiting", index=True)
    arrived_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, index=True)
    service_started_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    finished_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    # Duração prevista do atendimento (min). Se existir, o atendimento termina sozinho e liberta os recursos.
    service_minutes: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    is_simulated: Mapped[bool] = mapped_column(Boolean, default=True)  # todos os dados são sintéticos
    session_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("simulation_sessions.id", ondelete="CASCADE"), nullable=True, index=True
    )
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, onupdate=utcnow)

    vital_signs: Mapped[list["VitalSign"]] = relationship(
        back_populates="patient", cascade="all, delete-orphan", order_by="VitalSign.recorded_at, VitalSign.id"
    )
    symptoms: Mapped[list["Symptom"]] = relationship(
        back_populates="patient", cascade="all, delete-orphan", order_by="Symptom.id"
    )
    resource_requirements: Mapped[list["PatientResourceRequirement"]] = relationship(  # noqa: F821
        back_populates="patient", cascade="all, delete-orphan"
    )
    status_history: Mapped[list["PatientStatusHistory"]] = relationship(
        back_populates="patient", cascade="all, delete-orphan", order_by="PatientStatusHistory.id"
    )


class VitalSign(Base):
    """Unidades: temperature °C, heart_rate bpm, oxygen_saturation %, respiratory_rate rpm, pressões mmHg."""

    __tablename__ = "vital_signs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    patient_id: Mapped[int] = mapped_column(ForeignKey("patients.id", ondelete="CASCADE"), index=True)
    temperature: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    heart_rate: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    oxygen_saturation: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    respiratory_rate: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    systolic_pressure: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    diastolic_pressure: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    recorded_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)

    patient: Mapped[Patient] = relationship(back_populates="vital_signs")


class Symptom(Base):
    __tablename__ = "symptoms"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    patient_id: Mapped[int] = mapped_column(ForeignKey("patients.id", ondelete="CASCADE"), index=True)
    description: Mapped[str] = mapped_column(String(255))
    simulated_severity: Mapped[float] = mapped_column(Float)  # 0..10
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)

    patient: Mapped[Patient] = relationship(back_populates="symptoms")


class PatientStatusHistory(Base):
    __tablename__ = "patient_status_history"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    patient_id: Mapped[int] = mapped_column(ForeignKey("patients.id", ondelete="CASCADE"), index=True)
    old_status: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    new_status: Mapped[str] = mapped_column(String(20))
    changed_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)

    patient: Mapped[Patient] = relationship(back_populates="status_history")
