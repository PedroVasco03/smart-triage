from typing import Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.api.deps import get_clock, get_db
from app.core.clock import Clock
from app.schemas.statistics import DashboardOut, DistributionOut, EvolutionOut
from app.services.statistics_service import StatisticsService

router = APIRouter(prefix="/statistics", tags=["Estatísticas"])


@router.get("/dashboard", response_model=DashboardOut)
def dashboard(db: Session = Depends(get_db), clock: Clock = Depends(get_clock)):
    return StatisticsService(db, clock).dashboard()


@router.get("/priority-distribution", response_model=DistributionOut)
def distribution(db: Session = Depends(get_db), clock: Clock = Depends(get_clock)):
    return StatisticsService(db, clock).distribution()


@router.get("/utility-evolution", response_model=EvolutionOut)
def evolution(
    patient_id: Optional[int] = None,
    limit: int = Query(200, ge=1, le=2000),
    db: Session = Depends(get_db),
    clock: Clock = Depends(get_clock),
):
    return StatisticsService(db, clock).utility_evolution(patient_id, limit)
