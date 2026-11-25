"""Cenários sintéticos (combinações de gravidade, espera, risco e recursos)."""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Segment:
    profile: str
    share: float  # fração do total de pacientes
    start: float  # minutos desde o início
    spread: float  # janela de chegada (minutos)


@dataclass(frozen=True)
class Scenario:
    key: str
    name: str
    description: str
    segments: tuple[Segment, ...]
    default_capacity: dict[str, int]


_MIX = (
    Segment("mild", 0.40, 0, 240),
    Segment("moderate", 0.30, 0, 240),
    Segment("severe", 0.10, 0, 240),
    Segment("elderly_risk", 0.10, 0, 240),
    Segment("child_risk", 0.10, 0, 240),
)

SCENARIOS: dict[str, Scenario] = {
    s.key: s
    for s in (
        Scenario(
            "mixed_flow", "Fluxo misto",
            "Chegadas contínuas de casos ligeiros, moderados, graves e de risco etário.",
            _MIX, {"Médico": 2, "Cama": 3, "Oxigénio": 1},
        ),
        Scenario(
            "severe_vs_waiting", "Gravidade elevada vs. espera longa",
            "Muitos casos moderados chegam cedo e esperam muito; depois chegam casos graves com pouca espera.",
            (Segment("moderate", 0.60, 0, 30), Segment("severe", 0.40, 120, 60)),
            {"Médico": 3, "Cama": 3, "Oxigénio": 2},
        ),
        Scenario(
            "deterioration_risk", "Risco de agravamento",
            "Idosos e crianças pequenas misturados com casos ligeiros: o risco influencia a ordenação.",
            (Segment("elderly_risk", 0.35, 0, 180), Segment("child_risk", 0.25, 0, 180), Segment("mild", 0.40, 0, 180)),
            {"Médico": 2, "Cama": 3, "Oxigénio": 1},
        ),
        Scenario(
            "similar_scores", "Pontuações semelhantes",
            "Pacientes quase idênticos: as utilidades ficam muito próximas e os desempates são frequentes.",
            (Segment("moderate_tight", 1.0, 0, 90),),
            {"Médico": 2, "Cama": 3, "Oxigénio": 1},
        ),
        Scenario(
            "limited_resources", "Recursos limitados",
            "Fluxo misto com 1 médico, 1 cama e 1 posto de oxigénio.",
            _MIX, {"Médico": 1, "Cama": 1, "Oxigénio": 1},
        ),
    )
}
