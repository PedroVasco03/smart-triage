from datetime import datetime
from typing import Any, Optional

from sqlalchemy import JSON, Boolean, DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.core.clock import utcnow
from app.database.base import Base


class AgentConfiguration(Base):
    """Configurações versionadas (pesos e parâmetros). Só uma tem is_active=True."""

    __tablename__ = "agent_configurations"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    version: Mapped[int] = mapped_column(Integer, unique=True)
    weights: Mapped[dict[str, Any]] = mapped_column(JSON)
    params: Mapped[dict[str, Any]] = mapped_column(JSON)
    is_active: Mapped[bool] = mapped_column(Boolean, default=False, index=True)
    note: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)


class UtilityScore(Base):
    __tablename__ = "utility_scores"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    patient_id: Mapped[int] = mapped_column(ForeignKey("patients.id", ondelete="CASCADE"), index=True)
    config_id: Mapped[int] = mapped_column(ForeignKey("agent_configurations.id"), index=True)
    severity_score: Mapped[float] = mapped_column(Float)
    waiting_time_score: Mapped[float] = mapped_column(Float)
    deterioration_risk_score: Mapped[float] = mapped_column(Float)
    resource_score: Mapped[float] = mapped_column(Float)
    utility_score: Mapped[float] = mapped_column(Float)
    weights_configuration: Mapped[dict[str, Any]] = mapped_column(JSON)
    calculation_details: Mapped[dict[str, Any]] = mapped_column(JSON)
    trigger: Mapped[str] = mapped_column(String(40), default="manual")
    calculated_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, index=True)


class PriorityHistory(Base):
    __tablename__ = "priority_history"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    patient_id: Mapped[int] = mapped_column(ForeignKey("patients.id", ondelete="CASCADE"), index=True)
    config_id: Mapped[Optional[int]] = mapped_column(ForeignKey("agent_configurations.id"), nullable=True)
    previous_position: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    new_position: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    previous_utility: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    new_utility: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    trigger: Mapped[str] = mapped_column(String(40), default="manual")
    reason: Mapped[str] = mapped_column(Text)
    changed_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, index=True)


class QueueEntry(Base):
    """Estado atual da fila (uma linha por paciente em espera)."""

    __tablename__ = "queue_entries"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    patient_id: Mapped[int] = mapped_column(
        ForeignKey("patients.id", ondelete="CASCADE"), unique=True, index=True
    )
    position: Mapped[int] = mapped_column(Integer, index=True)
    utility_score: Mapped[float] = mapped_column(Float)
    config_id: Mapped[Optional[int]] = mapped_column(ForeignKey("agent_configurations.id"), nullable=True)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
