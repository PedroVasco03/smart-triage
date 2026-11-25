"""Cálculo dos fatores e da função de utilidade (funções puras, independentes da interface).

U(p) = (w1*G + w2*E + w3*R + w4*A) / (w1 + w2 + w3 + w4),   com G, E, R, A em [0, 100].

G  gravidade simulada      G = a*V + (1-a)*S
     V = m*max(d_i) + (1-m)*média(d_i), d_i = desvio do sinal vital i face ao intervalo de referência
     S = 10 * severidade máxima dos sintomas (0..10)
E  tempo de espera         E = 100 * (1 - exp(-t/tau))   (satura: nunca chega a 100)
R  risco de agravamento    R = r1*max(d_i) + r2*F_idade + r3*S   (r normalizados)
A  recursos (protegido)    A = A_raw + (100 - A_raw) * max(G, R)/100
"""
from __future__ import annotations

import math
from typing import Optional

from app.agents.domain import (
    FACTOR_LABELS,
    AgentParams,
    Evaluation,
    FactorScores,
    PatientObservation,
    ResourceNeed,
    Weights,
)
from datetime import datetime


def clip(x: float, lo: float = 0.0, hi: float = 100.0) -> float:
    return max(lo, min(hi, x))


def vital_deviation(value: float, rng: dict) -> float:
    """Desvio 0..100: 0 dentro do intervalo; sobe linearmente até 100 à distância `tol` do limite."""
    lo, hi = float(rng["min"]), float(rng["max"])
    if value < lo:
        dist, tol = lo - value, float(rng.get("tol_low", 0.0))
    elif value > hi:
        dist, tol = value - hi, float(rng.get("tol_high", 0.0))
    else:
        return 0.0
    if tol <= 0:
        return 100.0
    return clip(100.0 * dist / tol)


def vital_deviations(vitals: dict[str, float], ranges: dict[str, dict]) -> dict[str, float]:
    return {k: vital_deviation(float(v), ranges[k]) for k, v in vitals.items() if k in ranges and v is not None}


def vitals_score(devs: dict[str, float], max_share: float) -> Optional[float]:
    if not devs:
        return None
    values = list(devs.values())
    return clip(max_share * max(values) + (1.0 - max_share) * (sum(values) / len(values)))


def symptom_score(severities: tuple[float, ...]) -> float:
    return clip(10.0 * max(severities)) if severities else 0.0


def gravity_score(v: Optional[float], s: float, a: float) -> float:
    if v is None:
        return clip(s)
    return clip(a * v + (1.0 - a) * s)


def waiting_score(minutes: float, tau: float) -> float:
    if minutes <= 0:
        return 0.0
    return clip(100.0 * (1.0 - math.exp(-minutes / max(tau, 1e-9))))


def age_factor(age: float, p: AgentParams) -> float:
    young = 100.0 * clip((p.young_age - age) / max(p.young_age, 1e-9), 0.0, 1.0)
    old = 100.0 * clip((age - p.old_start) / max(p.old_full - p.old_start, 1e-9), 0.0, 1.0)
    return max(young, old)


def risk_score(max_dev: float, f_age: float, s: float, p: AgentParams) -> float:
    total = p.risk_vitals_share + p.risk_age_share + p.risk_symptom_share
    if total <= 0:
        return 0.0
    return clip((p.risk_vitals_share * max_dev + p.risk_age_share * f_age + p.risk_symptom_share * s) / total)


def raw_resource_availability(needs: tuple[ResourceNeed, ...], free: dict[int, int]) -> float:
    """% média de cobertura das necessidades (100 se o paciente não precisa de recursos)."""
    if not needs:
        return 100.0
    ratios = [min(max(free.get(n.resource_id, 0), 0) / max(n.quantity, 1), 1.0) for n in needs]
    return 100.0 * sum(ratios) / len(ratios)


def protected_resource_score(a_raw: float, g: float, r: float) -> float:
    """A falta de recursos penaliza cada vez menos quanto maior for max(G, R)."""
    protection = clip(max(g, r)) / 100.0
    return clip(a_raw + (100.0 - a_raw) * protection)


def waiting_minutes(arrived_at: datetime, now: datetime) -> float:
    return max(0.0, (now - arrived_at).total_seconds() / 60.0)


def compute_factors(
    obs: PatientObservation, now: datetime, free: dict[int, int], p: AgentParams
) -> FactorScores:
    notes: list[str] = []
    devs = vital_deviations(obs.vitals, p.vital_ranges)
    v = vitals_score(devs, p.vitals_max_share)
    s = symptom_score(obs.symptom_severities)
    if v is None:
        notes.append("Sem sinais vitais registados: gravidade baseada apenas nos sintomas.")
    if not obs.symptom_severities:
        notes.append("Sem sintomas registados: severidade dos sintomas considerada 0.")
    g = gravity_score(v, s, p.severity_vitals_share)
    max_dev = max(devs.values()) if devs else 0.0
    f_age = age_factor(obs.age, p)
    r = risk_score(max_dev, f_age, s, p)
    t = waiting_minutes(obs.arrived_at, now)
    e = waiting_score(t, p.tau_minutes)
    a_raw = raw_resource_availability(obs.needs, free)
    a = protected_resource_score(a_raw, g, r)
    if a_raw < 100.0 and a > a_raw + 1e-9:
        notes.append("Recursos em falta atenuados pela proteção ao risco (max de G e R).")
    return FactorScores(
        G=g, E=e, R=r, A=a, V=v, S=s, max_deviation=max_dev, age_factor=f_age,
        A_raw=a_raw, waiting_minutes=t, deviations=devs, notes=notes,
    )


def combine(f: FactorScores, weights: Weights) -> tuple[float, dict[str, float], dict[str, float]]:
    """Devolve (utilidade, pesos normalizados, contribuições por fator em pontos)."""
    w = weights.normalized()
    contributions = {"G": w.w1 * f.G, "E": w.w2 * f.E, "R": w.w3 * f.R, "A": w.w4 * f.A}
    utility = sum(contributions.values())
    return clip(utility), {"w1": w.w1, "w2": w.w2, "w3": w.w3, "w4": w.w4}, contributions


def priority_band(utility: float, bands: list[list]) -> str:
    for label, minimum in sorted(bands, key=lambda b: -float(b[1])):
        if utility >= float(minimum):
            return str(label)
    return str(bands[-1][0]) if bands else "-"


def _fmt(x: float) -> str:
    return f"{x:.1f}".replace(".", ",")


def _level(x: float) -> str:
    return "elevada" if x >= 70 else "moderada" if x >= 40 else "baixa"


def explain(ev: Evaluation) -> str:
    """Explicação legível da decisão, com os fatores e o respetivo contributo."""
    f, c = ev.factors, ev.contributions
    ordered = sorted(c.items(), key=lambda kv: -kv[1])
    top = [FACTOR_LABELS[k] for k, _ in ordered[:2]]
    parts = [
        f"Utilidade {_fmt(ev.utility)}/100 (prioridade simulada: {ev.band.lower()}).",
        f"Contribuições: gravidade {_fmt(c['G'])} pts (nível {_level(f.G)}), "
        f"risco de agravamento {_fmt(c['R'])} pts (nível {_level(f.R)}), "
        f"tempo de espera {_fmt(c['E'])} pts ({_fmt(f.waiting_minutes)} min), "
        f"recursos {_fmt(c['A'])} pts.",
        f"Pesaram sobretudo {top[0]} e {top[1]}.",
    ]
    parts.extend(f.notes)
    if ev.tie_break_applied:
        parts.append("Empate de utilidade resolvido por gravidade, risco, hora de chegada e identificador.")
    parts.append("Pontuação experimental de simulação académica; não é uma classificação clínica.")
    return " ".join(parts)
