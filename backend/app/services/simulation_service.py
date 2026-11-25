"""Sessões de simulação: executa o motor, persiste sessão, pacientes sintéticos e resultados."""
from __future__ import annotations

from datetime import timedelta
from typing import Any, Optional

import numpy as np
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.agents.domain import AgentConfig, Weights
from app.agents.utility_agent import UtilityAgent
from app.core.clock import Clock
from app.core.errors import NotFoundError, ValidationFailure
from app.models.patient import Patient, PatientStatusHistory, Symptom, VitalSign
from app.models.simulation import SimulationResult, SimulationSession
from app.schemas.common import ResourceNeedIn, SymptomIn, VitalSignsIn
from app.schemas.patient import PatientCreate
from app.schemas.simulation import GenerateRequest, SimulationCompare, SimulationStart
from app.services.config_service import ConfigService
from app.services.patient_service import PatientService
from app.services.resource_service import ResourceService
from app.simulation.engine import RunResult, build_population, run_simulation
from app.simulation.generators import generate_patient
from app.simulation.scenarios import SCENARIOS, Scenario


class SimulationService:
    def __init__(self, db: Session, clock: Clock):
        self.db = db
        self.clock = clock
        self.configs = ConfigService(db)

    # ------------------------------------------------------------------ catálogo
    @staticmethod
    def scenarios() -> list[dict[str, Any]]:
        return [
            {"key": s.key, "name": s.name, "description": s.description, "default_capacity": s.default_capacity}
            for s in SCENARIOS.values()
        ]

    @staticmethod
    def _scenario(key: str) -> Scenario:
        if key not in SCENARIOS:
            raise ValidationFailure(f"Cenário desconhecido: {key}.", {"valid": sorted(SCENARIOS)})
        return SCENARIOS[key]

    # ------------------------------------------------------------------ execução
    def start(self, req: SimulationStart) -> SimulationSession:
        scenario = self._scenario(req.scenario)
        weights = Weights.from_dict(req.weights_override.model_dump()) if req.weights_override else None
        return self._run_and_store(
            scenario, req.n_patients, req.duration_minutes, req.seed, req.capacity, weights,
            req.session_name or f"{scenario.name} (seed {req.seed})", req.description,
        )

    def compare(self, req: SimulationCompare) -> dict[str, Any]:
        scenario = self._scenario(req.scenario)
        runs = []
        for ws in req.weight_sets:
            weights = Weights.from_dict(ws.weights.model_dump())
            session = self._run_and_store(
                scenario, req.n_patients, req.duration_minutes, req.seed, req.capacity, weights,
                f"{ws.name} - {scenario.name}", "Comparação de configurações de pesos (mesma seed).",
            )
            runs.append(
                {"session_id": session.id, "name": ws.name, "weights": weights.to_dict(), "metrics": session.summary["metrics"]}
            )
        return {"scenario": scenario.key, "seed": req.seed, "runs": runs}

    def _run_and_store(
        self, scenario: Scenario, n: int, duration: int, seed: int, capacity_override: Optional[dict[str, int]],
        weights: Optional[Weights], name: str, description: Optional[str],
    ) -> SimulationSession:
        row = self.configs.get_active()
        cfg = ConfigService.to_domain(row)
        if weights is not None:
            try:
                weights.validate()
            except ValueError as e:
                raise ValidationFailure(str(e)) from e
            cfg = AgentConfig(version=cfg.version, weights=weights, params=cfg.params)
        capacity = {**scenario.default_capacity, **(capacity_override or {})}
        if any(v < 0 for v in capacity.values()):
            raise ValidationFailure("A capacidade não pode ser negativa.")

        rng = np.random.default_rng(seed)
        population = build_population(rng, scenario, n, float(duration), capacity)
        base = self.clock.now() - timedelta(minutes=duration)
        result = run_simulation(UtilityAgent(cfg), population, capacity, float(duration), base)

        session = SimulationSession(
            session_name=name,
            description=description,
            configuration={
                "scenario": scenario.key, "n_patients": n, "duration_minutes": duration, "seed": seed,
                "capacity": capacity, "weights": cfg.weights.to_dict(),
                "normalized_weights": cfg.weights.normalized().to_dict(),
                "config_version": cfg.version, "params": cfg.params.to_dict(),
            },
            status="completed",
        )
        self.db.add(session)
        self.db.flush()
        self._store_patients(session, result, base, duration)
        session.summary = {
            "metrics": result.metrics,
            "timeline": result.timeline,
            "final_queue": result.final_queue,
        }
        self.db.commit()
        return session

    def _store_patients(self, session: SimulationSession, result: RunResult, base, duration: int) -> None:
        pairs = []
        for sp in result.patients:
            syn = sp.synthetic
            if sp.start_min is None:
                status = "waiting"
            elif sp.finish_min is None:
                status = "in_service"
            else:
                status = "attended"
            arrived = base + timedelta(minutes=sp.arrival_min)
            p = Patient(
                patient_code=f"S{session.id:03d}-{sp.idx:03d}",
                age=syn.age, sex=syn.sex, status=status, arrived_at=arrived,
                service_started_at=None if sp.start_min is None else base + timedelta(minutes=sp.start_min),
                finished_at=None if sp.finish_min is None else base + timedelta(minutes=sp.finish_min),
                is_simulated=True, session_id=session.id,
            )
            p.vital_signs.append(VitalSign(recorded_at=arrived, **syn.vitals))
            for desc, sev in syn.symptoms:
                p.symptoms.append(Symptom(description=desc, simulated_severity=sev))
            p.status_history.append(PatientStatusHistory(old_status=None, new_status="waiting", changed_at=arrived))
            self.db.add(p)
            pairs.append((sp, p))
        self.db.flush()
        for sp, p in pairs:
            ev = sp.evaluation or {}
            wait = (sp.start_min if sp.start_min is not None else duration) - sp.arrival_min
            self.db.add(
                SimulationResult(
                    session_id=session.id,
                    patient_id=p.id,
                    utility_score=float(ev.get("utility", 0.0)),
                    assigned_position=sp.order,
                    waiting_minutes=round(wait, 2),
                    decision_explanation=ev.get("explanation", "Sem avaliação."),
                    details={
                        "profile": sp.synthetic.profile, "needs": sp.needs,
                        "arrival_min": sp.arrival_min, "start_min": sp.start_min, "finish_min": sp.finish_min,
                        "service_minutes": sp.synthetic.service_minutes, "evaluation": ev,
                        "evaluated_when": "ao ser chamado" if sp.start_min is not None else "no fim da simulação (ainda em espera)",
                    },
                )
            )

    # ------------------------------------------------------------------ consulta
    def sessions(self, limit: int = 100) -> list[dict[str, Any]]:
        rows = self.db.scalars(select(SimulationSession).order_by(SimulationSession.id.desc()).limit(limit))
        out = []
        for s in rows:
            m = (s.summary or {}).get("metrics", {})
            out.append(
                {
                    "id": s.id, "session_name": s.session_name,
                    "scenario": s.configuration.get("scenario"), "n_patients": s.configuration.get("n_patients"),
                    "seed": s.configuration.get("seed"), "avg_wait_minutes": m.get("avg_wait_minutes"),
                    "served": m.get("served"), "created_at": s.created_at,
                }
            )
        return out

    def session(self, session_id: int) -> SimulationSession:
        s = self.db.get(SimulationSession, session_id)
        if not s:
            raise NotFoundError("Sessão de simulação não encontrada")
        return s

    def results(self, session_id: int) -> list[dict[str, Any]]:
        self.session(session_id)
        stmt = (
            select(SimulationResult, Patient.patient_code)
            .join(Patient, Patient.id == SimulationResult.patient_id)
            .where(SimulationResult.session_id == session_id)
            .order_by(SimulationResult.assigned_position.is_(None), SimulationResult.assigned_position, SimulationResult.id)
        )
        return [
            {
                "id": r.id, "session_id": r.session_id, "patient_id": r.patient_id, "patient_code": code,
                "utility_score": round(r.utility_score, 2), "assigned_position": r.assigned_position,
                "waiting_minutes": r.waiting_minutes, "decision_explanation": r.decision_explanation, "details": r.details,
            }
            for r, code in self.db.execute(stmt)
        ]

    # ------------------------------------------------------------------ pacientes fictícios na fila real
    def generate_live(self, req: GenerateRequest) -> list[Patient]:
        rng = np.random.default_rng(req.seed)
        scenario = SCENARIOS["mixed_flow"]
        profiles = [seg.profile for seg in scenario.segments]
        shares = np.array([seg.share for seg in scenario.segments])
        resources = {r.resource_name: r.id for r in ResourceService(self.db).list()}
        psvc = PatientService(self.db, self.clock)
        now = self.clock.now()

        existing = {c for (c,) in self.db.execute(select(Patient.patient_code).where(Patient.patient_code.like("SYN-%")))}
        counter = len(existing)
        created: list[Patient] = []
        for _ in range(req.n):
            profile = str(rng.choice(profiles, p=shares / shares.sum()))
            syn = generate_patient(rng, profile)
            counter += 1
            code = f"SYN-{counter:04d}"
            while code in existing:
                counter += 1
                code = f"SYN-{counter:04d}"
            existing.add(code)
            data = PatientCreate(
                patient_code=code, age=syn.age, sex=syn.sex,
                vital_signs=VitalSignsIn(**syn.vitals),
                symptoms=[SymptomIn(description=d, simulated_severity=s) for d, s in syn.symptoms],
                required_resources=[ResourceNeedIn(resource_id=resources[n], quantity=q) for n, q in syn.needs.items() if n in resources],
                arrived_at=now - timedelta(minutes=float(rng.uniform(0, req.max_wait_minutes))),
                service_minutes=float(syn.service_minutes),
            )
            created.append(psvc.create(data, is_simulated=True))
        return created
