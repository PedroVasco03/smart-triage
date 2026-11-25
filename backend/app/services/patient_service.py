"""Persistência e regras de estado dos pacientes (não calcula prioridades)."""
from __future__ import annotations

from datetime import datetime, timedelta
from typing import Optional

from sqlalchemy import or_, select
from sqlalchemy.orm import Session, selectinload

from app.core.clock import Clock
from app.core.errors import ConflictError, NotFoundError, ValidationFailure
from app.models.patient import Patient, PatientStatusHistory, Symptom, VitalSign
from app.models.resource import PatientResourceRequirement, Resource
from app.schemas.patient import PatientCreate, PatientUpdate

ALLOWED_TRANSITIONS: dict[str, set[str]] = {
    "waiting": {"in_service", "left"},
    "in_service": {"attended", "left", "waiting"},
    "left": {"waiting"},
    "attended": set(),
}


def _load_options():
    return (
        selectinload(Patient.vital_signs),
        selectinload(Patient.symptoms),
        selectinload(Patient.resource_requirements).selectinload(PatientResourceRequirement.resource),
    )


class PatientService:
    def __init__(self, db: Session, clock: Clock):
        self.db = db
        self.clock = clock

    # --- consulta -----------------------------------------------------------------
    def get(self, patient_id: int) -> Patient:
        p = self.db.scalars(select(Patient).where(Patient.id == patient_id).options(*_load_options())).first()
        if not p:
            raise NotFoundError("Paciente não encontrado")
        return p

    def list(
        self,
        status: Optional[str] = None,
        session_id: Optional[int] = None,
        search: Optional[str] = None,
        skip: int = 0,
        limit: int = 100,
    ) -> list[Patient]:
        stmt = select(Patient).options(*_load_options())
        stmt = stmt.where(Patient.session_id == session_id) if session_id else stmt.where(Patient.session_id.is_(None))
        if status:
            stmt = stmt.where(Patient.status == status)
        if search:
            like = f"%{search.strip()}%"
            stmt = stmt.where(or_(Patient.patient_code.like(like.upper()), Patient.patient_code.like(like)))
        stmt = stmt.order_by(Patient.arrived_at.desc(), Patient.id.desc()).offset(skip).limit(limit)
        return list(self.db.scalars(stmt))

    # --- criação ------------------------------------------------------------------
    def _check_resources(self, needs) -> None:
        ids = {n.resource_id for n in needs}
        if len(ids) != len(needs):
            raise ValidationFailure("Recurso repetido na lista de recursos necessários.")
        if ids:
            found = set(self.db.scalars(select(Resource.id).where(Resource.id.in_(ids))))
            missing = ids - found
            if missing:
                raise ValidationFailure(f"Recurso(s) inexistente(s): {sorted(missing)}")

    def create(self, data: PatientCreate, session_id: Optional[int] = None, is_simulated: bool = True) -> Patient:
        if self.db.scalar(select(Patient.id).where(Patient.patient_code == data.patient_code)):
            raise ConflictError(f"Já existe um paciente com o código {data.patient_code}.")
        self._check_resources(data.required_resources)
        now = self.clock.now()
        p = Patient(
            patient_code=data.patient_code,
            age=data.age,
            sex=data.sex,
            status="waiting",
            arrived_at=data.arrived_at or now,
            is_simulated=is_simulated,
            session_id=session_id,
            service_minutes=data.service_minutes,
        )
        if data.vital_signs and data.vital_signs.provided():
            p.vital_signs.append(VitalSign(recorded_at=now, **data.vital_signs.provided()))
        for s in data.symptoms:
            p.symptoms.append(Symptom(description=s.description, simulated_severity=s.simulated_severity))
        for n in data.required_resources:
            p.resource_requirements.append(PatientResourceRequirement(resource_id=n.resource_id, quantity=n.quantity))
        p.status_history.append(PatientStatusHistory(old_status=None, new_status="waiting", changed_at=now))
        self.db.add(p)
        self.db.commit()
        return self.get(p.id)

    # --- atualização --------------------------------------------------------------
    def update(self, patient_id: int, data: PatientUpdate) -> tuple[Patient, str]:
        """Devolve (paciente, trigger). trigger = 'status_changed' ou 'patient_updated'."""
        p = self.get(patient_id)
        now = self.clock.now()
        trigger = "patient_updated"
        fields = data.model_fields_set

        if "age" in fields and data.age is not None:
            p.age = data.age
        if "sex" in fields:
            p.sex = data.sex
        if "arrived_at" in fields and data.arrived_at is not None:
            p.arrived_at = data.arrived_at
        if "service_minutes" in fields:
            p.service_minutes = data.service_minutes
        if "vital_signs" in fields and data.vital_signs and data.vital_signs.provided():
            p.vital_signs.append(VitalSign(recorded_at=now, **data.vital_signs.provided()))
        if "symptoms" in fields and data.symptoms is not None:
            p.symptoms.clear()
            self.db.flush()
            for s in data.symptoms:
                p.symptoms.append(Symptom(description=s.description, simulated_severity=s.simulated_severity))
        if "required_resources" in fields and data.required_resources is not None:
            if p.status == "in_service":
                raise ConflictError("Não é possível alterar os recursos de um paciente em atendimento.")
            self._check_resources(data.required_resources)
            p.resource_requirements.clear()
            self.db.flush()
            for n in data.required_resources:
                p.resource_requirements.append(PatientResourceRequirement(resource_id=n.resource_id, quantity=n.quantity))
        if "status" in fields and data.status is not None and data.status != p.status:
            self.transition_status(p, data.status)
            trigger = "status_changed"
        self.db.commit()
        return self.get(p.id), trigger

    def transition_status(self, p: Patient, new_status: str) -> None:
        old = p.status
        if new_status == old:
            return
        if new_status not in ALLOWED_TRANSITIONS.get(old, set()):
            raise ConflictError(f"Transição de estado inválida: {old} -> {new_status}.")
        now = self.clock.now()
        if new_status == "in_service":
            self._allocate(p)
            p.service_started_at = now
        if old == "in_service":
            self._release(p)
        if new_status in ("attended", "left"):
            p.finished_at = now
        if new_status == "waiting":
            p.service_started_at = None
            p.finished_at = None
        p.status = new_status
        p.status_history.append(PatientStatusHistory(old_status=old, new_status=new_status, changed_at=now))

    def _allocate(self, p: Patient) -> None:
        resources = {r.id: r for r in self.db.scalars(select(Resource).where(
            Resource.id.in_([q.resource_id for q in p.resource_requirements] or [0])))}
        for q in p.resource_requirements:
            r = resources[q.resource_id]
            if r.quantity_available - r.quantity_in_use < q.quantity:
                raise ConflictError(f"Recurso insuficiente: {r.resource_name}.")
        for q in p.resource_requirements:
            resources[q.resource_id].quantity_in_use += q.quantity

    def _release(self, p: Patient) -> None:
        for q in p.resource_requirements:
            r = self.db.get(Resource, q.resource_id)
            if r:
                r.quantity_in_use = max(r.quantity_in_use - q.quantity, 0)

    def delete(self, patient_id: int) -> None:
        p = self.get(patient_id)
        if p.status == "in_service":
            self._release(p)
        self.db.delete(p)
        self.db.commit()

    # --- apresentação -------------------------------------------------------------
    def latest_vitals(self, p: Patient) -> dict[str, float]:
        """Último valor conhecido de cada sinal vital (as leituras parciais são combinadas)."""
        merged: dict[str, float] = {}
        for v in p.vital_signs:
            for k in ("temperature", "heart_rate", "oxygen_saturation", "respiratory_rate", "systolic_pressure", "diastolic_pressure"):
                val = getattr(v, k)
                if val is not None:
                    merged[k] = val
        return merged

    def waiting_minutes(self, p: Patient) -> float:
        end = self.clock.now()
        if p.status in ("in_service", "attended", "left"):
            end = p.service_started_at or p.finished_at or end
        return round(max((end - p.arrived_at).total_seconds() / 60.0, 0.0), 2)

    def service_remaining(self, p: Patient) -> Optional[float]:
        if p.status != "in_service" or not p.service_minutes or not p.service_started_at:
            return None
        end = p.service_started_at + timedelta(minutes=p.service_minutes)
        return round(max((end - self.clock.now()).total_seconds() / 60.0, 0.0), 1)

    def to_out(self, p: Patient, queue_position: Optional[int] = None) -> dict:
        vitals = self.latest_vitals(p)
        last = p.vital_signs[-1] if p.vital_signs else None
        return {
            "id": p.id,
            "patient_code": p.patient_code,
            "age": p.age,
            "sex": p.sex,
            "status": p.status,
            "arrived_at": p.arrived_at,
            "service_started_at": p.service_started_at,
            "finished_at": p.finished_at,
            "is_simulated": p.is_simulated,
            "session_id": p.session_id,
            "waiting_minutes": self.waiting_minutes(p),
            "service_minutes": p.service_minutes,
            "service_remaining_minutes": self.service_remaining(p),
            "vital_signs": {**vitals, "recorded_at": last.recorded_at} if vitals else None,
            "symptoms": [{"id": s.id, "description": s.description, "simulated_severity": s.simulated_severity} for s in p.symptoms],
            "required_resources": [
                {"resource_id": q.resource_id, "resource_name": q.resource.resource_name, "quantity": q.quantity}
                for q in p.resource_requirements
            ],
            "queue_position": queue_position,
            "created_at": p.created_at,
            "updated_at": p.updated_at,
        }
