"""Agente baseado em utilidade.

Ciclo de decisão:
  perceive : recebe pacientes, recursos livres e o instante de avaliação
  process  : calcula os fatores G, E, R, A de cada paciente (normalizados em 0..100)
  evaluate : aplica os pesos, calcula U(p) e a explicação
  select   : ordena por utilidade (desempate determinístico) e escolhe o próximo paciente
             a atender respeitando os recursos disponíveis
"""
from __future__ import annotations

import heapq
from datetime import datetime
from typing import Optional

from app.agents.base_agent import BaseAgent
from app.agents.domain import (
    AgentConfig,
    BlockedPatient,
    Decision,
    Evaluation,
    FactorScores,
    PatientObservation,
    Percept,
)
from app.services import utility_service as us


def sort_key(ev: Evaluation) -> tuple:
    """Ordem total determinística: U desc, G desc, R desc, chegada asc, id asc."""
    return (-round(ev.utility, 6), -round(ev.factors.G, 6), -round(ev.factors.R, 6), ev.arrived_at, ev.patient_id)


class UtilityAgent(BaseAgent):
    def __init__(self, config: AgentConfig):
        config.weights.validate()
        self.config = config

    # --- Perceção -----------------------------------------------------------------
    def perceive(
        self, observations: list[PatientObservation], free_resources: dict[int, int], now: datetime
    ) -> Percept:
        seen: set[int] = set()
        unique: list[PatientObservation] = []
        for o in observations:
            if o.patient_id in seen:
                continue
            seen.add(o.patient_id)
            unique.append(o)
        return Percept(observations=tuple(unique), free_resources=dict(free_resources), now=now)

    # --- Processamento ------------------------------------------------------------
    def process(self, percept: Percept) -> list[tuple[PatientObservation, FactorScores]]:
        return [
            (o, us.compute_factors(o, percept.now, percept.free_resources, self.config.params))
            for o in percept.observations
        ]

    # --- Avaliação ----------------------------------------------------------------
    def evaluate(
        self, prepared: list[tuple[PatientObservation, FactorScores]], percept: Percept
    ) -> list[Evaluation]:
        out: list[Evaluation] = []
        for obs, factors in prepared:
            utility, weights, contributions = us.combine(factors, self.config.weights)
            ev = Evaluation(
                patient_id=obs.patient_id,
                patient_code=obs.patient_code,
                age=obs.age,
                arrived_at=obs.arrived_at,
                factors=factors,
                utility=utility,
                weights=weights,
                contributions=contributions,
                band=us.priority_band(utility, self.config.params.priority_bands),
            )
            out.append(ev)
        return out

    def rank(self, evaluations: list[Evaluation]) -> list[Evaluation]:
        ranked = sorted(evaluations, key=sort_key)
        for i, ev in enumerate(ranked):
            ev.position = i + 1
            same_prev = i > 0 and round(ranked[i - 1].utility, 6) == round(ev.utility, 6)
            same_next = i < len(ranked) - 1 and round(ranked[i + 1].utility, 6) == round(ev.utility, 6)
            ev.tie_break_applied = same_prev or same_next
            ev.explanation = us.explain(ev)
        return ranked

    def top_k(self, evaluations: list[Evaluation], k: int) -> list[Evaluation]:
        """k pacientes de maior prioridade sem ordenar a lista toda (heapq)."""
        return heapq.nsmallest(k, evaluations, key=sort_key)

    # --- Seleção ------------------------------------------------------------------
    def select(self, evaluations: list[Evaluation], percept: Percept) -> Decision:
        ranking = self.rank(evaluations)
        obs_by_id = {o.patient_id: o for o in percept.observations}
        free = dict(percept.free_resources)

        heap = [(sort_key(ev), i, ev) for i, ev in enumerate(ranking)]
        heapq.heapify(heap)
        blocked: list[BlockedPatient] = []
        chosen: Optional[Evaluation] = None
        while heap:
            _, _, ev = heapq.heappop(heap)
            missing = [
                {"resource_id": n.resource_id, "name": n.name, "needed": n.quantity, "free": max(free.get(n.resource_id, 0), 0)}
                for n in obs_by_id[ev.patient_id].needs
                if free.get(n.resource_id, 0) < n.quantity
            ]
            if not missing:
                chosen = ev
                break
            blocked.append(BlockedPatient(ev.patient_id, ev.patient_code, missing))

        log = [
            f"Perceção: {len(percept.observations)} paciente(s) em espera, instante {percept.now.isoformat()}.",
            "Processamento: fatores G, E, R, A calculados e normalizados em 0..100.",
            f"Avaliação: U(p) com pesos normalizados {self.config.weights.normalized().to_dict()}.",
        ]
        if chosen:
            log.append(
                f"Seleção: {chosen.patient_code} (U={chosen.utility:.2f}) é o próximo atendível; "
                f"{len(blocked)} paciente(s) à frente bloqueado(s) por falta de recursos."
            )
        else:
            log.append("Seleção: nenhum paciente atendível com os recursos atuais.")

        return Decision(
            evaluated_at=percept.now,
            config_version=self.config.version,
            ranking=ranking,
            next_patient_id=chosen.patient_id if chosen else None,
            blocked=blocked,
            cycle_log=log,
        )
