"""Schemas base. Unidades e intervalos de validação:
temperature 30-45 °C | heart_rate 20-250 bpm | oxygen_saturation 50-100 % |
respiratory_rate 4-70 rpm | systolic_pressure 50-260 mmHg | diastolic_pressure 30-160 mmHg |
age 0-120 anos | simulated_severity 0-10.
"""
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field, model_validator


class ORMModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)


class VitalSignsIn(BaseModel):
    temperature: Optional[float] = Field(None, ge=30, le=45, description="°C")
    heart_rate: Optional[float] = Field(None, ge=20, le=250, description="bpm")
    oxygen_saturation: Optional[float] = Field(None, ge=50, le=100, description="%")
    respiratory_rate: Optional[float] = Field(None, ge=4, le=70, description="respirações/min")
    systolic_pressure: Optional[float] = Field(None, ge=50, le=260, description="mmHg")
    diastolic_pressure: Optional[float] = Field(None, ge=30, le=160, description="mmHg")

    @model_validator(mode="after")
    def _pressures(self):
        s, d = self.systolic_pressure, self.diastolic_pressure
        if s is not None and d is not None and s <= d:
            raise ValueError("A pressão sistólica tem de ser maior que a diastólica.")
        return self

    def provided(self) -> dict[str, float]:
        return {k: v for k, v in self.model_dump().items() if v is not None}


class VitalSignsOut(ORMModel):
    temperature: Optional[float] = None
    heart_rate: Optional[float] = None
    oxygen_saturation: Optional[float] = None
    respiratory_rate: Optional[float] = None
    systolic_pressure: Optional[float] = None
    diastolic_pressure: Optional[float] = None
    recorded_at: Optional[datetime] = None


class SymptomIn(BaseModel):
    description: str = Field("sintoma", min_length=2, max_length=255)
    simulated_severity: float = Field(..., ge=0, le=10)


class SymptomOut(ORMModel):
    id: int
    description: str
    simulated_severity: float


class ResourceNeedIn(BaseModel):
    resource_id: int
    quantity: int = Field(1, ge=1, le=20)


class ResourceNeedOut(BaseModel):
    resource_id: int
    resource_name: str
    quantity: int
