from datetime import datetime, timezone
from typing import Literal, Optional

from pydantic import BaseModel, Field, field_validator

from app.schemas.common import ResourceNeedIn, ResourceNeedOut, SymptomIn, SymptomOut, VitalSignsIn, VitalSignsOut

Status = Literal["waiting", "in_service", "attended", "left"]


def _to_naive_utc(v: Optional[datetime]) -> Optional[datetime]:
    """O backend trabalha com UTC sem tzinfo; datas com fuso (ex.: 'Z') são convertidas."""
    if v is not None and v.tzinfo is not None:
        return v.astimezone(timezone.utc).replace(tzinfo=None)
    return v


class PatientCreate(BaseModel):
    patient_code: str = Field(..., min_length=1, max_length=32, pattern=r"^[A-Za-z0-9_\-]+$")
    age: int = Field(..., ge=0, le=120)
    sex: Optional[Literal["M", "F"]] = None
    vital_signs: Optional[VitalSignsIn] = None
    symptoms: list[SymptomIn] = Field(default_factory=list, max_length=20)
    required_resources: list[ResourceNeedIn] = Field(default_factory=list, max_length=10)
    arrived_at: Optional[datetime] = None  # por defeito: agora
    service_minutes: Optional[float] = Field(None, ge=1, le=1440, description="Duração prevista do atendimento (min)")

    @field_validator("patient_code")
    @classmethod
    def _upper(cls, v: str) -> str:
        return v.strip().upper()

    @field_validator("arrived_at")
    @classmethod
    def _utc(cls, v):
        return _to_naive_utc(v)


class PatientUpdate(BaseModel):
    age: Optional[int] = Field(None, ge=0, le=120)
    sex: Optional[Literal["M", "F"]] = None
    status: Optional[Status] = None
    arrived_at: Optional[datetime] = None
    service_minutes: Optional[float] = Field(None, ge=1, le=1440)
    vital_signs: Optional[VitalSignsIn] = None  # acrescenta uma nova leitura (histórico)
    symptoms: Optional[list[SymptomIn]] = Field(None, max_length=20)  # substitui a lista
    required_resources: Optional[list[ResourceNeedIn]] = Field(None, max_length=10)  # substitui

    @field_validator("arrived_at")
    @classmethod
    def _utc(cls, v):
        return _to_naive_utc(v)


class PatientOut(BaseModel):
    id: int
    patient_code: str
    age: int
    sex: Optional[str]
    status: str
    arrived_at: datetime
    service_started_at: Optional[datetime]
    finished_at: Optional[datetime]
    is_simulated: bool
    session_id: Optional[int]
    waiting_minutes: float
    service_minutes: Optional[float] = None
    service_remaining_minutes: Optional[float] = None
    vital_signs: Optional[VitalSignsOut]
    symptoms: list[SymptomOut]
    required_resources: list[ResourceNeedOut]
    queue_position: Optional[int] = None
    created_at: datetime
    updated_at: datetime
