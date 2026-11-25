"""Motor de simulação orientado a eventos (SimPy) que usa o MESMO agente da fila real.

- O relógio virtual (minutos simulados) alimenta o tempo de espera do agente.
- Recursos: contadores de unidades livres por tipo (ex.: Médico, Cama, Oxigénio).
- Sempre que há uma chegada ou um atendimento termina, o agente corre um ciclo e chama os
  pacientes que consegue atender, por ordem de utilidade e respeitando os recursos.
- Necessidades de recursos que não existem na capacidade do cenário são ignoradas.
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Optional

import numpy as np
import simpy

from app.agents.domain import PatientObservation, ResourceNeed
from app.agents.utility_agent import UtilityAgent
from app.core.clock import VirtualClock
from app.simulation.generators import SyntheticPatient, generate_patient
from app.simulation.scenarios import Scenario


@dataclass
class SimPatient:
    idx: int
    synthetic: SyntheticPatient
    arrival_min: float
    needs: dict[str, int]
    start_min: Optional[float] = None
    finish_min: Optional[float] = None
    order: Optional[int] = None
    evaluation: Optional[dict[str, Any]] = None  # avaliação ao ser chamado (ou final, se não atendido)


@dataclass
class RunResult:
    patients: list[SimPatient]
    timeline: list[dict[str, Any]]
    metrics: dict[str, Any]
    final_queue: list[dict[str, Any]] = field(default_factory=list)


def _allocate(total: int, shares: list[float]) -> list[int]:
    """Maior resto: distribui `total` pacientes pelos segmentos de forma exata e determinística."""
    s = sum(shares)
    raw = [total * x / s for x in shares]
    base = [int(math.floor(r)) for r in raw]
    rest = total - sum(base)
    order = sorted(range(len(raw)), key=lambda i: (-(raw[i] - base[i]), i))
    for i in order[:rest]:
        base[i] += 1
    return base


def build_population(rng: np.random.Generator, scenario: Scenario, n: int, duration: float, capacity: dict[str, int]) -> list[SimPatient]:
    counts = _allocate(n, [seg.share for seg in scenario.segments])
    raw: list[tuple[float, SyntheticPatient]] = []
    for seg, count in zip(scenario.segments, counts):
        for _ in range(count):
            syn = generate_patient(rng, seg.profile)
            window = max(min(seg.spread, duration - seg.start), 0.0)
            arrival = seg.start + float(rng.uniform(0, window)) if window > 0 else min(seg.start, duration - 1)
            raw.append((round(min(arrival, duration - 1), 2), syn))
    raw.sort(key=lambda t: t[0])  # estável: empates mantêm a ordem de geração
    pop: list[SimPatient] = []
    for i, (arrival, syn) in enumerate(raw, start=1):
        needs = {k: v for k, v in syn.needs.items() if capacity.get(k, 0) >= 1}
        pop.append(SimPatient(idx=i, synthetic=syn, arrival_min=arrival, needs=needs))
    return pop


def run_simulation(
    agent: UtilityAgent,
    population: list[SimPatient],
    capacity: dict[str, int],
    duration: float,
    start_time: datetime,
    sample_every: float = 5.0,
) -> RunResult:
    env = simpy.Environment()
    clock = VirtualClock(start_time, lambda: env.now)
    names = sorted(capacity)
    rid = {n: i + 1 for i, n in enumerate(names)}
    free = {rid[n]: int(capacity[n]) for n in names}
    busy_minutes = {n: 0.0 for n in names}
    by_idx = {p.idx: p for p in population}
    waiting: list[SimPatient] = []
    wake = [env.event()]
    counter = {"order": 0}
    timeline: list[dict[str, Any]] = []

    def notify() -> None:
        if not wake[0].triggered:
            wake[0].succeed()

    def observation(p: SimPatient) -> PatientObservation:
        syn = p.synthetic
        return PatientObservation(
            patient_id=p.idx,
            patient_code=f"SIM-{p.idx:03d}",
            age=syn.age,
            arrived_at=start_time + _minutes(p.arrival_min),
            vitals=dict(syn.vitals),
            symptom_severities=tuple(sev for _, sev in syn.symptoms),
            needs=tuple(ResourceNeed(rid[n], n, q) for n, q in p.needs.items()),
        )

    def cycle():
        return agent.run_cycle([observation(p) for p in waiting], dict(free), clock.now())

    def service(p: SimPatient):
        yield env.timeout(p.synthetic.service_minutes)
        for n, q in p.needs.items():
            free[rid[n]] += q
        p.finish_min = env.now
        notify()

    def dispatch() -> None:
        while waiting:
            decision = cycle()
            if decision.next_patient_id is None:
                break
            ev = next(e for e in decision.ranking if e.patient_id == decision.next_patient_id)
            p = by_idx[decision.next_patient_id]
            waiting.remove(p)
            for n, q in p.needs.items():
                free[rid[n]] -= q
                busy_minutes[n] += q * min(p.synthetic.service_minutes, max(duration - env.now, 0.0))
            counter["order"] += 1
            p.start_min, p.order, p.evaluation = env.now, counter["order"], ev.to_dict()
            env.process(service(p))

    def dispatcher():
        while True:
            yield wake[0]
            wake[0] = env.event()
            dispatch()

    def arrival(p: SimPatient):
        yield env.timeout(p.arrival_min)
        waiting.append(p)
        notify()

    def sampler():
        while True:
            if waiting:
                d = cycle()
                avg_u = sum(e.utility for e in d.ranking) / len(d.ranking)
                max_wait = max(e.factors.waiting_minutes for e in d.ranking)
            else:
                avg_u, max_wait = None, 0.0
            in_service = sum(1 for p in population if p.start_min is not None and p.finish_min is None)
            timeline.append(
                {"t": round(env.now, 1), "queue_length": len(waiting), "in_service": in_service,
                 "avg_utility": None if avg_u is None else round(avg_u, 2), "max_wait": round(max_wait, 1)}
            )
            yield env.timeout(sample_every)

    env.process(dispatcher())
    env.process(sampler())
    for p in population:
        env.process(arrival(p))
    env.run(until=duration)

    final_queue: list[dict[str, Any]] = []
    if waiting:
        decision = cycle()
        for e in decision.ranking:
            by_idx[e.patient_id].evaluation = e.to_dict()
            final_queue.append({"patient_id": e.patient_id, "position": e.position, "utility": round(e.utility, 2)})

    metrics = _metrics(population, duration, capacity, busy_minutes)
    return RunResult(population, timeline, metrics, final_queue)


def _minutes(m: float):
    from datetime import timedelta

    return timedelta(minutes=m)


def _mean(xs: list[float]) -> Optional[float]:
    return round(float(np.mean(xs)), 2) if xs else None


def _metrics(pop: list[SimPatient], duration: float, capacity: dict[str, int], busy: dict[str, float]) -> dict[str, Any]:
    served = [p for p in pop if p.start_min is not None]
    waits = [p.start_min - p.arrival_min for p in served]  # type: ignore[operator]

    def g(p: SimPatient) -> float:
        return float(p.evaluation["factors"]["G"]) if p.evaluation else 0.0

    high = [p.start_min - p.arrival_min for p in served if g(p) >= 60]  # type: ignore[operator]
    mid = [p.start_min - p.arrival_min for p in served if 30 <= g(p) < 60]  # type: ignore[operator]
    low = [p.start_min - p.arrival_min for p in served if g(p) < 30]  # type: ignore[operator]
    unserved_high = sum(1 for p in pop if p.start_min is None and g(p) >= 60)
    return {
        "n_patients": len(pop),
        "served": len(served),
        "unserved": len(pop) - len(served),
        "unserved_high_severity": unserved_high,
        "avg_wait_minutes": _mean(waits),
        "max_wait_minutes": round(max(waits), 2) if waits else None,
        "p90_wait_minutes": round(float(np.percentile(waits, 90)), 2) if waits else None,
        "avg_wait_high_severity": _mean(high),
        "avg_wait_medium_severity": _mean(mid),
        "avg_wait_low_severity": _mean(low),
        "avg_utility_at_service": _mean([p.evaluation["utility"] for p in served if p.evaluation]),
        "resource_utilization": {
            n: round(min(busy[n] / (capacity[n] * duration), 1.0), 3) if capacity[n] > 0 else 0.0 for n in capacity
        },
    }
