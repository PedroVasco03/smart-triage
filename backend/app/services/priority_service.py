"""Gestão dinâmica da fila: ação e reavaliação do agente.

Fluxo: evento (novo paciente, atualização, estado, recursos, pesos, passagem do tempo)
  -> recalculate(trigger) -> UtilityAgent.run_cycle (puro) -> persiste fila, pontuações e histórico.

Nota sobre heapq: as prioridades mudam com o tempo (E cresce), por isso todas as chaves ficam
obsoletas a cada reavaliação. O recálculo completo + ordenação é O(n log n) e mais simples do que
manter um heap com invalidação. O heap é usado para extrair os k primeiros e na seleção do próximo
paciente atendível (ver UtilityAgent).
"""
from __future__ import annotations

from datetime import timedelta
from typing import Any, Optional

from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload

from app.agents.domain import (
    AgentConfig,
    Decision,
    Evaluation,
    PatientObservation,
    ResourceNeed,
    Weights,
)
from app.agents.utility_agent import UtilityAgent
from app.core.clock import Clock
from app.core.errors import NotFoundError, ValidationFailure
from app.models.agent import AgentConfiguration, PriorityHistory, QueueEntry, UtilityScore
from app.models.patient import Patient
from app.models.resource import PatientResourceRequirement, Resource
from app.schemas.agent import EvaluateRequest
from app.services.config_service import ConfigService
from app.services.patient_service import PatientService
from app.services.resource_service import ResourceService

REASONS = {
    "patient_created": "Novo paciente registado",
    "patient_updated": "Dados do paciente atualizados",
    "status_changed": "Estado do paciente alterado",
    "resources_changed": "Disponibilidade de recursos alterada",
    "config_changed": "Pesos/parâmetros do agente alterados",
    "time_elapsed": "Passagem do tempo de espera",
    "time_advanced": "Tempo de espera avançado manualmente",
    "patients_generated": "Pacientes fictícios gerados",
    "manual": "Recálculo manual",
}

# Eventos que mudam dados dos pacientes: registam sempre histórico/pontuações.
ALWAYS_PERSIST = {k for k in REASONS if k != "time_elapsed"}


class PriorityService:
    def __init__(self, db: Session, clock: Clock):
        self.db = db
        self.clock = clock
        self.configs = ConfigService(db)
        self.patients = PatientService(db, clock)
        self.resources = ResourceService(db)
        self.last_completed: list[str] = []

    # ------------------------------------------------------------------ percepção
    def _waiting(self) -> list[Patient]:
        stmt = (
            select(Patient)
            .where(Patient.status == "waiting", Patient.session_id.is_(None))
            .options(
                selectinload(Patient.vital_signs),
                selectinload(Patient.symptoms),
                selectinload(Patient.resource_requirements).selectinload(PatientResourceRequirement.resource),
            )
            .order_by(Patient.id)
        )
        return list(self.db.scalars(stmt))

    def _observation(self, p: Patient) -> PatientObservation:
        return PatientObservation(
            patient_id=p.id,
            patient_code=p.patient_code,
            age=p.age,
            arrived_at=p.arrived_at,
            vitals=self.patients.latest_vitals(p),
            symptom_severities=tuple(float(s.simulated_severity) for s in p.symptoms),
            needs=tuple(ResourceNeed(q.resource_id, q.resource.resource_name, q.quantity) for q in p.resource_requirements),
        )

    def _agent(self, weights_override: Optional[dict] = None) -> tuple[UtilityAgent, AgentConfiguration]:
        row = self.configs.get_active()
        cfg = ConfigService.to_domain(row)
        if weights_override:
            cfg = AgentConfig(version=cfg.version, weights=Weights.from_dict(weights_override), params=cfg.params)
        return UtilityAgent(cfg), row

    def compute(self) -> tuple[Decision, dict[int, Patient], AgentConfiguration]:
        """Corre um ciclo do agente sobre a fila atual, sem persistir."""
        agent, row = self._agent()
        patients = self._waiting()
        decision = agent.run_cycle(
            [self._observation(p) for p in patients], self.resources.free_map(), self.clock.now()
        )
        return decision, {p.id: p for p in patients}, row

    # ------------------------------------------------------------------ ação
    def complete_due_services(self) -> list[str]:
        """Termina os atendimentos cuja duração prevista já passou e liberta os recursos."""
        now = self.clock.now()
        stmt = (
            select(Patient)
            .where(
                Patient.status == "in_service", Patient.session_id.is_(None),
                Patient.service_minutes.is_not(None), Patient.service_started_at.is_not(None),
            )
            .options(selectinload(Patient.resource_requirements))
            .order_by(Patient.id)
        )
        done: list[str] = []
        for p in self.db.scalars(stmt):
            end = p.service_started_at + timedelta(minutes=p.service_minutes)
            if end <= now:
                self.patients.transition_status(p, "attended")
                p.finished_at = end
                done.append(p.patient_code)
                self.db.add(
                    PriorityHistory(
                        patient_id=p.id, previous_position=None, new_position=None, trigger="status_changed",
                        reason=f"Atendimento concluído após {p.service_minutes:g} min; recursos libertados.",
                        changed_at=now,
                    )
                )
        if done:
            self.db.commit()
        return done

    def recalculate(self, trigger: str = "manual", force: bool = False, reason: Optional[str] = None):
        done = self.complete_due_services()
        self.last_completed = done
        if done:
            note = f"Atendimento concluído: {', '.join(done)}"
            if trigger == "time_elapsed":
                trigger, reason = "status_changed", note
            else:
                reason = f"{reason or REASONS.get(trigger, trigger)} ({note})"
        decision, patients, cfg_row = self.compute()
        prev = {qe.patient_id: qe for qe in self.db.scalars(select(QueueEntry))}
        new_pos = {ev.patient_id: ev.position for ev in decision.ranking}

        order_changed = set(prev) != set(new_pos) or any(prev[pid].position != pos for pid, pos in new_pos.items())
        config_changed = any(qe.config_id != cfg_row.id for qe in prev.values())
        if trigger in ALWAYS_PERSIST or force or order_changed or config_changed:
            self._persist(decision, patients, cfg_row, prev, trigger, reason)
        return decision, patients, cfg_row

    def _persist(self, decision, patients, cfg_row, prev, trigger, reason) -> None:
        now = decision.evaluated_at
        base = reason or REASONS.get(trigger, trigger)
        weights_snapshot = cfg_row.weights

        for ev in decision.ranking:
            f = ev.factors
            self.db.add(
                UtilityScore(
                    patient_id=ev.patient_id,
                    config_id=cfg_row.id,
                    severity_score=f.G,
                    waiting_time_score=f.E,
                    deterioration_risk_score=f.R,
                    resource_score=f.A,
                    utility_score=ev.utility,
                    weights_configuration=weights_snapshot,
                    calculation_details=ev.to_dict(),
                    trigger=trigger,
                    calculated_at=now,
                )
            )
            old = prev.get(ev.patient_id)
            moved = old is None or old.position != ev.position
            if moved or trigger in ALWAYS_PERSIST:
                self.db.add(
                    PriorityHistory(
                        patient_id=ev.patient_id,
                        config_id=cfg_row.id,
                        previous_position=old.position if old else None,
                        new_position=ev.position,
                        previous_utility=old.utility_score if old else None,
                        new_utility=ev.utility,
                        trigger=trigger,
                        reason=f"{base}: posição {old.position if old else '-'} -> {ev.position}; "
                        f"utilidade {old.utility_score:.1f} -> {ev.utility:.1f}."
                        if old
                        else f"{base}: entrou na fila na posição {ev.position} (utilidade {ev.utility:.1f}).",
                        changed_at=now,
                    )
                )
            if old:
                old.position, old.utility_score, old.config_id, old.updated_at = ev.position, ev.utility, cfg_row.id, now
            else:
                self.db.add(QueueEntry(patient_id=ev.patient_id, position=ev.position, utility_score=ev.utility, config_id=cfg_row.id, updated_at=now))

        new_ids = {ev.patient_id for ev in decision.ranking}
        for pid, old in prev.items():
            if pid in new_ids:
                continue
            exists = self.db.get(Patient, pid)
            if exists is not None:
                self.db.add(
                    PriorityHistory(
                        patient_id=pid, config_id=cfg_row.id, previous_position=old.position, new_position=None,
                        previous_utility=old.utility_score, new_utility=None, trigger=trigger,
                        reason=f"{base}: saiu da fila (estado: {exists.status}).", changed_at=now,
                    )
                )
            self.db.delete(old)
        self.db.commit()

    # ------------------------------------------------------------------ consulta
    def _missing(self, p: Patient, free: dict[int, int]) -> list[dict[str, Any]]:
        return [
            {"resource_id": q.resource_id, "name": q.resource.resource_name, "needed": q.quantity, "free": max(free.get(q.resource_id, 0), 0)}
            for q in p.resource_requirements
            if free.get(q.resource_id, 0) < q.quantity
        ]

    def get_queue(self) -> dict[str, Any]:
        decision, patients, _ = self.recalculate("time_elapsed")
        free = self.resources.free_map()
        items = []
        for ev in decision.ranking:
            p = patients[ev.patient_id]
            items.append(
                {
                    "position": ev.position,
                    "patient_id": p.id,
                    "patient_code": p.patient_code,
                    "age": p.age,
                    "symptoms": [s.description for s in p.symptoms],
                    "waiting_minutes": round(ev.factors.waiting_minutes, 2),
                    "utility_score": round(ev.utility, 2),
                    "band": ev.band,
                    "status": p.status,
                    "tie_break_applied": ev.tie_break_applied,
                    "blocked_by_resources": bool(self._missing(p, free)),
                    "last_evaluated_at": decision.evaluated_at,
                    "contributions": {k: round(v, 2) for k, v in ev.contributions.items()},
                }
            )
        return {
            "evaluated_at": decision.evaluated_at,
            "config_version": decision.config_version,
            "next_patient_id": decision.next_patient_id,
            "items": items,
        }

    def get_detail(self, patient_id: int) -> dict[str, Any]:
        decision, patients, _ = self.recalculate("time_elapsed")
        ev = next((e for e in decision.ranking if e.patient_id == patient_id), None)
        if ev is not None:
            p = patients[patient_id]
            missing = self._missing(p, self.resources.free_map())
            return self._detail(p, ev.to_dict(), True, True, decision.evaluated_at, decision.config_version, missing)

        p = self.patients.get(patient_id)  # 404 se não existir
        last = self.db.scalars(
            select(UtilityScore).where(UtilityScore.patient_id == patient_id).order_by(UtilityScore.id.desc())
        ).first()
        if last is None:
            raise NotFoundError("Este paciente ainda não tem avaliação do agente.")
        cfg = self.db.get(AgentConfiguration, last.config_id)
        return self._detail(p, last.calculation_details, False, False, last.calculated_at, cfg.version if cfg else None, [])

    def _detail(self, p, ev_dict, in_queue, live, at, version, missing) -> dict[str, Any]:
        out = self.patients.to_out(p)
        return {
            "patient_id": p.id,
            "patient_code": p.patient_code,
            "age": p.age,
            "status": p.status,
            "in_queue": in_queue,
            "live": live,
            "evaluated_at": at,
            "config_version": version,
            "evaluation": ev_dict,
            "symptoms": out["symptoms"],
            "vital_signs": out["vital_signs"],
            "blocked_by_resources": bool(missing),
            "missing_resources": missing,
        }

    def history(self, limit: int = 100, patient_id: Optional[int] = None) -> list[dict[str, Any]]:
        stmt = (
            select(PriorityHistory, Patient.patient_code)
            .join(Patient, Patient.id == PriorityHistory.patient_id, isouter=True)
            .order_by(PriorityHistory.id.desc())
            .limit(limit)
        )
        if patient_id:
            stmt = stmt.where(PriorityHistory.patient_id == patient_id)
        out = []
        for h, code in self.db.execute(stmt):
            out.append(
                {
                    "id": h.id, "patient_id": h.patient_id, "patient_code": code,
                    "previous_position": h.previous_position, "new_position": h.new_position,
                    "previous_utility": None if h.previous_utility is None else round(h.previous_utility, 2),
                    "new_utility": None if h.new_utility is None else round(h.new_utility, 2),
                    "trigger": h.trigger, "reason": h.reason, "config_id": h.config_id, "changed_at": h.changed_at,
                }
            )
        return out

    # ------------------------------------------------------------------ ações do agente
    def call_next(self) -> dict[str, Any]:
        decision, patients, _ = self.recalculate("time_elapsed")
        if not patients:
            return {"called": False, "message": "A fila está vazia."}
        if decision.next_patient_id is None:
            return {"called": False, "message": "Nenhum paciente pode ser atendido com os recursos livres atuais."}
        p = patients[decision.next_patient_id]
        blocked = [b.patient_code for b in decision.blocked]
        self.patients.transition_status(p, "in_service")
        self.db.commit()
        note = f"{p.patient_code} chamado para atendimento"
        if blocked:
            note += f" (à frente, sem recursos: {', '.join(blocked)})"
        self.recalculate("status_changed", reason=note)
        return {"called": True, "message": note + ".", "patient_id": p.id, "patient_code": p.patient_code}

    def advance_time(self, minutes: float) -> int:
        """Equivale a avançar o relógio: recua a hora de chegada dos pacientes em espera."""
        waiting = self._waiting()
        for p in waiting:
            p.arrived_at = p.arrived_at - timedelta(minutes=minutes)
        in_service = self.db.scalars(
            select(Patient).where(Patient.status == "in_service", Patient.session_id.is_(None))
        ).all()
        for p in in_service:  # os atendimentos em curso também "envelhecem" e podem terminar
            if p.service_started_at:
                p.service_started_at = p.service_started_at - timedelta(minutes=minutes)
        self.db.commit()
        self.recalculate("time_advanced", reason=f"Tempo avançado {minutes:g} min")
        return len(waiting)

    def status(self) -> dict[str, Any]:
        decision, patients, row = self.compute()
        last = self.db.scalar(select(func.max(UtilityScore.calculated_at)))
        total = self.db.scalar(select(func.count(UtilityScore.id))) or 0
        in_service = self.db.scalar(
            select(func.count(Patient.id)).where(Patient.status == "in_service", Patient.session_id.is_(None))
        ) or 0
        return {
            "agent_type": "Agente baseado em utilidade",
            "config_version": row.version,
            "queue_size": len(patients),
            "in_service": in_service,
            "last_evaluation_at": last,
            "total_evaluations": total,
            "decision_cycle": ["Perceção", "Processamento", "Avaliação", "Seleção", "Ação", "Reavaliação"],
        }

    # ------------------------------------------------------------------ avaliação "e se"
    def evaluate_adhoc(self, req: EvaluateRequest) -> dict[str, Any]:
        override = req.weights_override.model_dump() if req.weights_override else None
        if override:
            try:
                Weights.from_dict(override).validate()
            except ValueError as e:
                raise ValidationFailure(str(e)) from e
        agent, row = self._agent(override)
        now = self.clock.now()
        free = self.resources.free_map()
        names = {r.id: r.resource_name for r in self.resources.list()}

        observations: list[PatientObservation] = []
        if req.hypothetical:
            for i, h in enumerate(req.hypothetical, start=1):
                for n in h.required_resources:
                    if n.resource_id not in names:
                        raise ValidationFailure(f"Recurso inexistente: {n.resource_id}")
                observations.append(
                    PatientObservation(
                        patient_id=-i,
                        patient_code=f"{h.label}-{i}",
                        age=h.age,
                        arrived_at=now - timedelta(minutes=h.waiting_minutes),
                        vitals=h.vital_signs.provided() if h.vital_signs else {},
                        symptom_severities=tuple(s.simulated_severity for s in h.symptoms),
                        needs=tuple(ResourceNeed(n.resource_id, names[n.resource_id], n.quantity) for n in h.required_resources),
                    )
                )
        if req.patient_ids or not req.hypothetical:
            pool = self._waiting() if not req.patient_ids else [self.patients.get(i) for i in req.patient_ids]
            observations.extend(self._observation(p) for p in pool)

        decision = agent.run_cycle(observations, free, now)
        return {
            "evaluated_at": decision.evaluated_at,
            "config_version": decision.config_version,
            "weights_used": agent.config.weights.normalized().to_dict(),
            "evaluations": [e.to_dict() for e in decision.ranking],
            "next_patient_id": decision.next_patient_id,
            "cycle_log": decision.cycle_log,
        }
