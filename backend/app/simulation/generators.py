"""Geração de pacientes sintéticos (nenhum dado real). Reprodutível através de uma seed."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import numpy as np

# (média, desvio) por sinal vital; severidade (min, max); idade (min, max); necessidades (prob.); serviço (média, desvio, min)
PROFILES: dict[str, dict[str, Any]] = {
    "mild": {
        "age": (18, 60), "sev": (1, 4), "service": (12, 3),
        "vitals": {"temperature": (37.0, 0.4), "heart_rate": (78, 9), "oxygen_saturation": (97.5, 1.0),
                   "respiratory_rate": (16, 2), "systolic_pressure": (120, 9), "diastolic_pressure": (78, 6)},
        "needs": {"Cama": 0.05, "Oxigénio": 0.0},
        "symptoms": ["tosse ligeira", "dor de cabeça", "dor muscular", "náuseas ligeiras"],
    },
    "moderate": {
        "age": (5, 80), "sev": (4, 7), "service": (25, 6),
        "vitals": {"temperature": (38.2, 0.6), "heart_rate": (104, 10), "oxygen_saturation": (93.5, 1.5),
                   "respiratory_rate": (22, 3), "systolic_pressure": (132, 12), "diastolic_pressure": (84, 8)},
        "needs": {"Cama": 0.5, "Oxigénio": 0.15},
        "symptoms": ["febre persistente", "falta de ar moderada", "dor abdominal", "vómitos repetidos"],
    },
    "severe": {
        "age": (1, 90), "sev": (7.5, 10), "service": (45, 10),
        "vitals": {"temperature": (39.3, 0.6), "heart_rate": (130, 12), "oxygen_saturation": (87, 3),
                   "respiratory_rate": (29, 4), "systolic_pressure": (88, 12), "diastolic_pressure": (55, 8)},
        "needs": {"Cama": 0.9, "Oxigénio": 0.7},
        "symptoms": ["dificuldade respiratória grave", "dor torácica intensa", "confusão mental", "hemorragia"],
    },
    "elderly_risk": {
        "age": (72, 92), "sev": (3, 6), "service": (30, 8),
        "vitals": {"temperature": (37.9, 0.5), "heart_rate": (96, 10), "oxygen_saturation": (94, 1.5),
                   "respiratory_rate": (20, 3), "systolic_pressure": (150, 14), "diastolic_pressure": (88, 8)},
        "needs": {"Cama": 0.4, "Oxigénio": 0.2},
        "symptoms": ["tontura", "falta de ar ao esforço", "fraqueza", "queda recente"],
    },
    "child_risk": {
        "age": (0, 4), "sev": (3, 7), "service": (20, 5),
        "vitals": {"temperature": (38.8, 0.5), "heart_rate": (118, 10), "oxygen_saturation": (95, 1.5),
                   "respiratory_rate": (28, 3), "systolic_pressure": (100, 8), "diastolic_pressure": (62, 6)},
        "needs": {"Cama": 0.3, "Oxigénio": 0.1},
        "symptoms": ["febre alta", "recusa alimentar", "irritabilidade", "respiração rápida"],
    },
    "moderate_tight": {  # perfis quase idênticos -> pontuações de utilidade muito próximas
        "age": (40, 44), "sev": (5, 5.5), "service": (25, 2),
        "vitals": {"temperature": (38.0, 0.1), "heart_rate": (104, 2), "oxygen_saturation": (94, 0.3),
                   "respiratory_rate": (22, 0.5), "systolic_pressure": (130, 2), "diastolic_pressure": (84, 2)},
        "needs": {"Cama": 0.5, "Oxigénio": 0.1},
        "symptoms": ["febre persistente", "falta de ar moderada"],
    },
}

VITAL_LIMITS = {
    "temperature": (30.0, 45.0), "heart_rate": (20.0, 250.0), "oxygen_saturation": (50.0, 100.0),
    "respiratory_rate": (4.0, 70.0), "systolic_pressure": (50.0, 260.0), "diastolic_pressure": (30.0, 160.0),
}


@dataclass
class SyntheticPatient:
    profile: str
    age: int
    sex: str
    vitals: dict[str, float]
    symptoms: list[tuple[str, float]]
    needs: dict[str, int]  # nome do recurso -> quantidade
    service_minutes: float


def generate_patient(rng: np.random.Generator, profile: str) -> SyntheticPatient:
    cfg = PROFILES[profile]
    vitals: dict[str, float] = {}
    for key, (mean, sd) in cfg["vitals"].items():
        lo, hi = VITAL_LIMITS[key]
        vitals[key] = round(float(np.clip(rng.normal(mean, sd), lo, hi)), 1)
    if vitals["systolic_pressure"] <= vitals["diastolic_pressure"]:
        vitals["diastolic_pressure"] = round(vitals["systolic_pressure"] - 15, 1)

    n_sym = int(rng.integers(1, 3))
    names = list(rng.choice(cfg["symptoms"], size=min(n_sym, len(cfg["symptoms"])), replace=False))
    lo, hi = cfg["sev"]
    symptoms = [(str(n), round(float(rng.uniform(lo, hi)), 1)) for n in names]

    needs: dict[str, int] = {"Médico": 1}
    for res, prob in cfg["needs"].items():
        if rng.random() < prob:
            needs[res] = 1

    mean, sd = cfg["service"]
    service = max(5.0, float(rng.normal(mean, sd)))
    age_lo, age_hi = cfg["age"]
    return SyntheticPatient(
        profile=profile,
        age=int(rng.integers(age_lo, age_hi + 1)),
        sex=str(rng.choice(["M", "F"])),
        vitals=vitals,
        symptoms=symptoms,
        needs=needs,
        service_minutes=round(service, 1),
    )
