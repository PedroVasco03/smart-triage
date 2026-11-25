from typing import Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.api.deps import get_clock, get_db
from app.core.clock import Clock
from app.schemas.queue import CallNextOut, HistoryItem, QueueDetailOut, QueueOut
from app.services.priority_service import PriorityService

router = APIRouter(prefix="/queue", tags=["Fila de prioridades"])


@router.get("", response_model=QueueOut, summary="Fila ordenada pela utilidade (reavaliada no momento)")
def get_queue(db: Session = Depends(get_db), clock: Clock = Depends(get_clock)):
    return PriorityService(db, clock).get_queue()


@router.get("/history", response_model=list[HistoryItem])
def queue_history(
    limit: int = Query(100, ge=1, le=1000),
    patient_id: Optional[int] = None,
    db: Session = Depends(get_db),
    clock: Clock = Depends(get_clock),
):
    return PriorityService(db, clock).history(limit, patient_id)


@router.post("/recalculate", response_model=QueueOut)
def recalculate(db: Session = Depends(get_db), clock: Clock = Depends(get_clock)):
    svc = PriorityService(db, clock)
    svc.recalculate("manual", force=True)
    return svc.get_queue()


@router.post("/call-next", response_model=CallNextOut, summary="Chamar o próximo paciente atendível")
def call_next(db: Session = Depends(get_db), clock: Clock = Depends(get_clock)):
    return PriorityService(db, clock).call_next()


@router.get("/{patient_id}", response_model=QueueDetailOut, summary="Detalhe e explicação da decisão")
def queue_detail(patient_id: int, db: Session = Depends(get_db), clock: Clock = Depends(get_clock)):
    return PriorityService(db, clock).get_detail(patient_id)
