from datetime import datetime
from typing import Any, Optional

from pydantic import BaseModel

from app.schemas.agent import EvaluationOut
from app.schemas.common import SymptomOut, VitalSignsOut


class QueueItem(BaseModel):
    position: int
    patient_id: int
    patient_code: str
    age: int
    symptoms: list[str]
    waiting_minutes: float
    utility_score: float
    band: str
    status: str
    tie_break_applied: bool
    blocked_by_resources: bool = False
    last_evaluated_at: datetime
    contributions: dict[str, float]


class QueueOut(BaseModel):
    evaluated_at: datetime
    config_version: int
    next_patient_id: Optional[int]
    items: list[QueueItem]


class QueueDetailOut(BaseModel):
    patient_id: int
    patient_code: str
    age: int
    status: str
    in_queue: bool
    live: bool  # False = última avaliação guardada (paciente já não está na fila)
    evaluated_at: datetime
    config_version: Optional[int]
    evaluation: EvaluationOut
    symptoms: list[SymptomOut]
    vital_signs: Optional[VitalSignsOut]
    blocked_by_resources: bool = False
    missing_resources: list[dict[str, Any]] = []


class HistoryItem(BaseModel):
    id: int
    patient_id: int
    patient_code: Optional[str]
    previous_position: Optional[int]
    new_position: Optional[int]
    previous_utility: Optional[float]
    new_utility: Optional[float]
    trigger: str
    reason: str
    config_id: Optional[int]
    changed_at: datetime


class CallNextOut(BaseModel):
    called: bool
    message: str
    patient_id: Optional[int] = None
    patient_code: Optional[str] = None
