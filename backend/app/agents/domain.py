"""Tipos de domínio do agente (puros, sem BD nem API).

Escalas: todos os fatores G, E, R, A vivem em [0, 100].
Unidades e intervalos de referência são PARÂMETROS EXPERIMENTAIS desta simulação académica;
não constituem protocolo clínico validado.
"""
from __future__ import annotations

import copy
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Optional

VITAL_KEYS = (
    "temperature",
    "heart_rate",
    "oxygen_saturation",
    "respiratory_rate",
    "systolic_pressure",
    "diastolic_pressure",
)

# min/max: intervalo de referência (desvio 0). tol_*: distância fora do intervalo que dá desvio 100.
DEFAULT_VITAL_RANGES: dict[str, dict[str, Any]] = {
    "temperature": {"min": 36.0, "max": 37.5, "tol_low": 3.0, "tol_high": 2.5, "unit": "°C"},
    "heart_rate": {"min": 60, "max": 100, "tol_low": 20, "tol_high": 50, "unit": "bpm"},
    "oxygen_saturation": {"min": 95, "max": 100, "tol_low": 10, "tol_high": 1, "unit": "%"},
    "respiratory_rate": {"min": 12, "max": 20, "tol_low": 5, "tol_high": 12, "unit": "rpm"},
    "systolic_pressure": {"min": 100, "max": 140, "tol_low": 40, "tol_high": 50, "unit": "mmHg"},
    "diastolic_pressure": {"min": 60, "max": 90, "tol_low": 25, "tol_high": 30, "unit": "mmHg"},
}

DEFAULT_PRIORITY_BANDS: list[list[Any]] = [["Muito alta", 75], ["Alta", 55], ["Média", 35], ["Baixa", 0]]

FACTOR_LABELS = {
    "G": "gravidade simulada",
    "E": "tempo de espera",
    "R": "risco de agravamento",
    "A": "disponibilidade de recursos",
}


@dataclass(frozen=True)
class Weights:
    """Pesos w1..w4 (gravidade, espera, risco, recursos). Aceita qualquer escala; é normalizado pela soma."""

    w1: float = 40.0
    w2: float = 20.0
    w3: float = 30.0
    w4: float = 10.0

    def total(self) -> float:
        return self.w1 + self.w2 + self.w3 + self.w4

    def validate(self) -> list[str]:
        """Lança ValueError se inválido; devolve avisos (não bloqueantes)."""
        vals = (self.w1, self.w2, self.w3, self.w4)
        if any(v < 0 for v in vals):
            raise ValueError("Os pesos não podem ser negativos.")
        if self.total() <= 0:
            raise ValueError("A soma dos pesos tem de ser maior que zero.")
        warnings: list[str] = []
        if self.w2 >= self.w1:
            warnings.append(
                "O peso do tempo de espera é igual ou superior ao da gravidade: a espera pode "
                "ultrapassar a gravidade na ordenação."
            )
        return warnings

    def normalized(self) -> "Weights":
        t = self.total()
        return Weights(self.w1 / t, self.w2 / t, self.w3 / t, self.w4 / t)

    def to_dict(self) -> dict[str, float]:
        return {"w1": self.w1, "w2": self.w2, "w3": self.w3, "w4": self.w4}

    @classmethod
    def from_dict(cls, d: dict[str, Any] | None) -> "Weights":
        d = d or {}
        base = cls()
        return cls(
            float(d.get("w1", base.w1)),
            float(d.get("w2", base.w2)),
            float(d.get("w3", base.w3)),
            float(d.get("w4", base.w4)),
        )


@dataclass(frozen=True)
class AgentParams:
    tau_minutes: float = 60.0  # constante de tempo da saturação do fator E
    severity_vitals_share: float = 0.6  # G = a*V + (1-a)*S
    vitals_max_share: float = 0.5  # V = m*max(d) + (1-m)*média(d)
    risk_vitals_share: float = 0.5  # R = r1*max(d) + r2*F_idade + r3*S (normalizados pela soma)
    risk_age_share: float = 0.3
    risk_symptom_share: float = 0.2
    young_age: float = 5.0  # F_idade = 100 aos 0 anos, 0 aos young_age
    old_start: float = 60.0  # F_idade = 0 até old_start, 100 em old_full
    old_full: float = 90.0
    vital_ranges: dict[str, dict[str, Any]] = field(default_factory=lambda: copy.deepcopy(DEFAULT_VITAL_RANGES))
    priority_bands: list[list[Any]] = field(default_factory=lambda: copy.deepcopy(DEFAULT_PRIORITY_BANDS))

    def to_dict(self) -> dict[str, Any]:
        return {
            "tau_minutes": self.tau_minutes,
            "severity_vitals_share": self.severity_vitals_share,
            "vitals_max_share": self.vitals_max_share,
            "risk_vitals_share": self.risk_vitals_share,
            "risk_age_share": self.risk_age_share,
            "risk_symptom_share": self.risk_symptom_share,
            "young_age": self.young_age,
            "old_start": self.old_start,
            "old_full": self.old_full,
            "vital_ranges": copy.deepcopy(self.vital_ranges),
            "priority_bands": copy.deepcopy(self.priority_bands),
        }

    @classmethod
    def from_dict(cls, d: dict[str, Any] | None) -> "AgentParams":
        d = dict(d or {})
        base = cls()
        ranges = copy.deepcopy(DEFAULT_VITAL_RANGES)
        for key, override in (d.pop("vital_ranges", None) or {}).items():
            if key in ranges and isinstance(override, dict):
                ranges[key].update(override)
        bands = d.pop("priority_bands", None) or copy.deepcopy(DEFAULT_PRIORITY_BANDS)
        scalars = {k: float(v) for k, v in d.items() if hasattr(base, k) and k not in ("vital_ranges", "priority_bands")}
        return cls(vital_ranges=ranges, priority_bands=bands, **scalars)


@dataclass(frozen=True)
class AgentConfig:
    version: int = 0
    weights: Weights = field(default_factory=Weights)
    params: AgentParams = field(default_factory=AgentParams)

    def to_dict(self) -> dict[str, Any]:
        return {"version": self.version, "weights": self.weights.to_dict(), "params": self.params.to_dict()}


@dataclass(frozen=True)
class ResourceNeed:
    resource_id: int
    name: str
    quantity: int = 1


@dataclass(frozen=True)
class PatientObservation:
    """O que o agente perceciona sobre um paciente num instante."""

    patient_id: int
    patient_code: str
    age: int
    arrived_at: datetime
    vitals: dict[str, float] = field(default_factory=dict)  # só os valores fornecidos
    symptom_severities: tuple[float, ...] = ()  # 0..10
    needs: tuple[ResourceNeed, ...] = ()


@dataclass(frozen=True)
class Percept:
    observations: tuple[PatientObservation, ...]
    free_resources: dict[int, int]  # resource_id -> unidades livres
    now: datetime


@dataclass
class FactorScores:
    G: float
    E: float
    R: float
    A: float
    V: Optional[float]  # desvio agregado dos sinais vitais (None se não houver vitais)
    S: float  # severidade máxima dos sintomas (0..100)
    max_deviation: float
    age_factor: float
    A_raw: float
    waiting_minutes: float
    deviations: dict[str, float]
    notes: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        r = lambda x: None if x is None else round(float(x), 4)  # noqa: E731
        return {
            "G": r(self.G), "E": r(self.E), "R": r(self.R), "A": r(self.A),
            "V": r(self.V), "S": r(self.S), "max_deviation": r(self.max_deviation),
            "age_factor": r(self.age_factor), "A_raw": r(self.A_raw),
            "waiting_minutes": r(self.waiting_minutes),
            "deviations": {k: r(v) for k, v in self.deviations.items()},
            "notes": list(self.notes),
        }


@dataclass
class Evaluation:
    patient_id: int
    patient_code: str
    age: int
    arrived_at: datetime
    factors: FactorScores
    utility: float
    weights: dict[str, float]  # normalizados (soma 1)
    contributions: dict[str, float]  # pontos de utilidade por fator
    band: str
    explanation: str = ""
    position: int = 0
    tie_break_applied: bool = False

    def to_dict(self) -> dict[str, Any]:
        return {
            "patient_id": self.patient_id,
            "patient_code": self.patient_code,
            "utility": round(self.utility, 4),
            "position": self.position,
            "band": self.band,
            "factors": self.factors.to_dict(),
            "weights": {k: round(v, 6) for k, v in self.weights.items()},
            "contributions": {k: round(v, 4) for k, v in self.contributions.items()},
            "explanation": self.explanation,
            "tie_break_applied": self.tie_break_applied,
        }


@dataclass
class BlockedPatient:
    patient_id: int
    patient_code: str
    missing: list[dict[str, Any]]


@dataclass
class Decision:
    """Resultado de um ciclo do agente."""

    evaluated_at: datetime
    config_version: int
    ranking: list[Evaluation]
    next_patient_id: Optional[int]
    blocked: list[BlockedPatient]
    cycle_log: list[str]
