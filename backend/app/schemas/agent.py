from datetime import datetime
from typing import Any, Optional

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.schemas.common import ResourceNeedIn, SymptomIn, VitalSignsIn


class WeightsSchema(BaseModel):
    """Pesos em qualquer escala (ex.: 40/20/30/10 ou 0.4/0.2/0.3/0.1); são normalizados pela soma."""

    w1: float = Field(40, ge=0, description="gravidade")
    w2: float = Field(20, ge=0, description="tempo de espera")
    w3: float = Field(30, ge=0, description="risco de agravamento")
    w4: float = Field(10, ge=0, description="disponibilidade de recursos")

    @model_validator(mode="after")
    def _sum(self):
        if self.w1 + self.w2 + self.w3 + self.w4 <= 0:
            raise ValueError("A soma dos pesos tem de ser maior que zero.")
        return self


class VitalRangeSchema(BaseModel):
    model_config = ConfigDict(extra="forbid")
    min: Optional[float] = None
    max: Optional[float] = None
    tol_low: Optional[float] = Field(None, ge=0)
    tol_high: Optional[float] = Field(None, ge=0)


class ParamsSchema(BaseModel):
    """Parâmetros experimentais (todos opcionais; o que não vier mantém o valor atual)."""

    model_config = ConfigDict(extra="forbid")
    tau_minutes: Optional[float] = Field(None, ge=5, le=1440)
    severity_vitals_share: Optional[float] = Field(None, ge=0, le=1)
    vitals_max_share: Optional[float] = Field(None, ge=0, le=1)
    risk_vitals_share: Optional[float] = Field(None, ge=0)
    risk_age_share: Optional[float] = Field(None, ge=0)
    risk_symptom_share: Optional[float] = Field(None, ge=0)
    young_age: Optional[float] = Field(None, ge=1, le=18)
    old_start: Optional[float] = Field(None, ge=30, le=100)
    old_full: Optional[float] = Field(None, ge=31, le=120)
    vital_ranges: Optional[dict[str, VitalRangeSchema]] = None
    priority_bands: Optional[list[list[Any]]] = None

    @model_validator(mode="after")
    def _check(self):
        if self.old_start is not None and self.old_full is not None and self.old_full <= self.old_start:
            raise ValueError("old_full tem de ser maior que old_start.")
        if self.priority_bands is not None:
            for b in self.priority_bands:
                if len(b) != 2 or not isinstance(b[0], str):
                    raise ValueError("Cada faixa tem o formato [nome, mínimo].")
        return self


class ConfigUpdate(BaseModel):
    weights: Optional[WeightsSchema] = None
    params: Optional[ParamsSchema] = None
    note: Optional[str] = Field(None, max_length=255)


class ConfigOut(BaseModel):
    id: int
    version: int
    is_active: bool
    weights: dict[str, float]
    normalized_weights: dict[str, float]
    params: dict[str, Any]
    note: Optional[str]
    warnings: list[str] = []
    created_at: datetime


class HypotheticalPatient(BaseModel):
    label: str = Field("hipotético", max_length=32)
    age: int = Field(..., ge=0, le=120)
    vital_signs: Optional[VitalSignsIn] = None
    symptoms: list[SymptomIn] = Field(default_factory=list)
    required_resources: list[ResourceNeedIn] = Field(default_factory=list)
    waiting_minutes: float = Field(0, ge=0, le=100000)


class EvaluateRequest(BaseModel):
    """Avaliação sem persistência (cenários "e se"). Sem patient_ids nem hypothetical: avalia a fila atual."""

    patient_ids: Optional[list[int]] = None
    hypothetical: Optional[list[HypotheticalPatient]] = Field(None, max_length=100)
    weights_override: Optional[WeightsSchema] = None


class FactorsOut(BaseModel):
    G: float
    E: float
    R: float
    A: float
    V: Optional[float]
    S: float
    max_deviation: float
    age_factor: float
    A_raw: float
    waiting_minutes: float
    deviations: dict[str, float]
    notes: list[str]


class EvaluationOut(BaseModel):
    patient_id: int
    patient_code: str
    position: int
    utility: float
    band: str
    factors: FactorsOut
    weights: dict[str, float]
    contributions: dict[str, float]
    explanation: str
    tie_break_applied: bool


class EvaluateResponse(BaseModel):
    evaluated_at: datetime
    config_version: int
    weights_used: dict[str, float]
    evaluations: list[EvaluationOut]
    next_patient_id: Optional[int]
    cycle_log: list[str]


class AgentStatusOut(BaseModel):
    agent_type: str
    config_version: int
    queue_size: int
    in_service: int
    last_evaluation_at: Optional[datetime]
    total_evaluations: int
    decision_cycle: list[str]
