from datetime import datetime
from typing import Any, Optional

from pydantic import BaseModel, Field

from app.schemas.agent import WeightsSchema


class SimulationStart(BaseModel):
    scenario: str = Field("mixed_flow", description="Chave de /simulation/scenarios")
    session_name: Optional[str] = Field(None, max_length=120)
    description: Optional[str] = None
    n_patients: int = Field(40, ge=1, le=300)
    duration_minutes: int = Field(480, ge=30, le=2880)
    seed: int = Field(42, ge=0)
    weights_override: Optional[WeightsSchema] = None
    capacity: Optional[dict[str, int]] = Field(None, description="Ex.: {'Médico': 2, 'Cama': 3, 'Oxigénio': 1}")


class WeightSet(BaseModel):
    name: str = Field(..., max_length=60)
    weights: WeightsSchema


class SimulationCompare(BaseModel):
    scenario: str = "mixed_flow"
    n_patients: int = Field(40, ge=1, le=300)
    duration_minutes: int = Field(480, ge=30, le=2880)
    seed: int = Field(42, ge=0)
    capacity: Optional[dict[str, int]] = None
    weight_sets: list[WeightSet] = Field(..., min_length=2, max_length=6)


class GenerateRequest(BaseModel):
    n: int = Field(8, ge=1, le=100)
    seed: int = Field(1, ge=0)
    max_wait_minutes: int = Field(90, ge=0, le=1440)


class AdvanceTime(BaseModel):
    minutes: float = Field(..., gt=0, le=1440)


class SessionOut(BaseModel):
    id: int
    session_name: str
    description: Optional[str]
    status: str
    configuration: dict[str, Any]
    summary: Optional[dict[str, Any]]
    created_at: datetime


class SessionListItem(BaseModel):
    id: int
    session_name: str
    scenario: Optional[str]
    n_patients: Optional[int]
    seed: Optional[int]
    avg_wait_minutes: Optional[float]
    served: Optional[int]
    created_at: datetime


class ResultOut(BaseModel):
    id: int
    session_id: int
    patient_id: int
    patient_code: str
    utility_score: float
    assigned_position: Optional[int]
    waiting_minutes: Optional[float]
    decision_explanation: str
    details: Optional[dict[str, Any]]


class ScenarioOut(BaseModel):
    key: str
    name: str
    description: str
    default_capacity: dict[str, int]
