from datetime import datetime
from typing import Any, Optional

from pydantic import BaseModel


class RecentActivity(BaseModel):
    patient_code: Optional[str]
    trigger: str
    reason: str
    changed_at: datetime


class DashboardOut(BaseModel):
    total_patients: int
    in_queue: int
    in_service: int
    attended: int
    average_utility: Optional[float]
    config_version: int
    distribution: list[dict[str, Any]]
    recent_activity: list[RecentActivity]


class DistributionOut(BaseModel):
    total: int
    bands: list[dict[str, Any]]


class EvolutionPoint(BaseModel):
    t: datetime
    avg_utility: Optional[float] = None
    max_utility: Optional[float] = None
    n: Optional[int] = None
    utility: Optional[float] = None
    G: Optional[float] = None
    E: Optional[float] = None
    R: Optional[float] = None
    A: Optional[float] = None


class EvolutionOut(BaseModel):
    patient_id: Optional[int]
    points: list[EvolutionPoint]
