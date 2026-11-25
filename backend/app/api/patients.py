from typing import Optional

from fastapi import APIRouter, Depends, Query, Response
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import get_clock, get_db
from app.core.clock import Clock
from app.models.agent import QueueEntry
from app.schemas.patient import PatientCreate, PatientOut, PatientUpdate, Status
from app.services.patient_service import PatientService
from app.services.priority_service import PriorityService

router = APIRouter(prefix="/patients", tags=["Pacientes"])


def _position(db: Session, patient_id: int) -> Optional[int]:
    return db.scalar(select(QueueEntry.position).where(QueueEntry.patient_id == patient_id))


@router.post("", response_model=PatientOut, status_code=201, summary="Registar paciente (dados sintéticos)")
def create_patient(data: PatientCreate, db: Session = Depends(get_db), clock: Clock = Depends(get_clock)):
    svc = PatientService(db, clock)
    p = svc.create(data, is_simulated=False)
    PriorityService(db, clock).recalculate("patient_created", reason=f"Novo paciente {p.patient_code}")
    return svc.to_out(p, _position(db, p.id))


@router.get("", response_model=list[PatientOut], summary="Listar pacientes")
def list_patients(
    status: Optional[Status] = None,
    session_id: Optional[int] = Query(None, description="Sem valor: só pacientes da fila real (fora de simulações)"),
    search: Optional[str] = None,
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    db: Session = Depends(get_db),
    clock: Clock = Depends(get_clock),
):
    PriorityService(db, clock).complete_due_services()  # atendimentos cuja duração acabou
    svc = PatientService(db, clock)
    return [svc.to_out(p, _position(db, p.id)) for p in svc.list(status, session_id, search, skip, limit)]


@router.get("/{patient_id}", response_model=PatientOut)
def get_patient(patient_id: int, db: Session = Depends(get_db), clock: Clock = Depends(get_clock)):
    svc = PatientService(db, clock)
    return svc.to_out(svc.get(patient_id), _position(db, patient_id))


@router.put("/{patient_id}", response_model=PatientOut, summary="Atualizar paciente (reavalia a fila)")
def update_patient(patient_id: int, data: PatientUpdate, db: Session = Depends(get_db), clock: Clock = Depends(get_clock)):
    svc = PatientService(db, clock)
    p, trigger = svc.update(patient_id, data)
    PriorityService(db, clock).recalculate(trigger, reason=f"{p.patient_code}")
    return svc.to_out(svc.get(patient_id), _position(db, patient_id))


@router.delete("/{patient_id}", status_code=204)
def delete_patient(patient_id: int, db: Session = Depends(get_db), clock: Clock = Depends(get_clock)):
    PatientService(db, clock).delete(patient_id)
    PriorityService(db, clock).recalculate("status_changed", reason="Paciente removido")
    return Response(status_code=204)
