from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.api.deps import get_clock, get_db
from app.core.clock import Clock
from app.schemas.patient import PatientOut
from app.schemas.simulation import (
    AdvanceTime, GenerateRequest, ResultOut, ScenarioOut, SessionListItem, SessionOut,
    SimulationCompare, SimulationStart,
)
from app.services.patient_service import PatientService
from app.services.priority_service import PriorityService
from app.services.simulation_service import SimulationService

router = APIRouter(prefix="/simulation", tags=["Simulação"])


@router.get("/scenarios", response_model=list[ScenarioOut])
def scenarios():
    return SimulationService.scenarios()


@router.post("/start", response_model=SessionOut, status_code=201, summary="Executar um cenário simulado")
def start(body: SimulationStart, db: Session = Depends(get_db), clock: Clock = Depends(get_clock)):
    return SimulationService(db, clock).start(body)


@router.post("/compare", summary="Mesmo cenário e seed com vários conjuntos de pesos")
def compare(body: SimulationCompare, db: Session = Depends(get_db), clock: Clock = Depends(get_clock)):
    return SimulationService(db, clock).compare(body)


@router.get("/sessions", response_model=list[SessionListItem])
def sessions(limit: int = Query(100, ge=1, le=500), db: Session = Depends(get_db), clock: Clock = Depends(get_clock)):
    return SimulationService(db, clock).sessions(limit)


@router.get("/sessions/{session_id}", response_model=SessionOut)
def session(session_id: int, db: Session = Depends(get_db), clock: Clock = Depends(get_clock)):
    return SimulationService(db, clock).session(session_id)


@router.get("/sessions/{session_id}/results", response_model=list[ResultOut])
def session_results(session_id: int, db: Session = Depends(get_db), clock: Clock = Depends(get_clock)):
    return SimulationService(db, clock).results(session_id)


@router.post("/generate", response_model=list[PatientOut], status_code=201, summary="Gerar pacientes fictícios na fila")
def generate(body: GenerateRequest, db: Session = Depends(get_db), clock: Clock = Depends(get_clock)):
    created = SimulationService(db, clock).generate_live(body)
    PriorityService(db, clock).recalculate("patients_generated", reason=f"{len(created)} paciente(s) fictício(s)")
    psvc = PatientService(db, clock)
    return [psvc.to_out(psvc.get(p.id)) for p in created]


@router.post("/advance-time", summary="Avançar o tempo de espera de todos os pacientes em espera")
def advance_time(body: AdvanceTime, db: Session = Depends(get_db), clock: Clock = Depends(get_clock)):
    svc = PriorityService(db, clock)
    n = svc.advance_time(body.minutes)
    return {"advanced_minutes": body.minutes, "patients_affected": n, "services_completed": svc.last_completed}
