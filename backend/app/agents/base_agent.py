"""Contrato do agente: ciclo Perceção -> Processamento -> Avaliação -> Seleção.

A etapa de Ação (persistir fila e histórico) e de Reavaliação (disparar um novo ciclo quando o
ambiente muda) pertencem à camada de serviços, que é quem tem acesso à base de dados.
O agente em si é puro: mesmos dados + mesma configuração => mesma decisão.
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from datetime import datetime
from typing import Any

from app.agents.domain import Decision, Evaluation, PatientObservation, Percept


class BaseAgent(ABC):
    @abstractmethod
    def perceive(
        self, observations: list[PatientObservation], free_resources: dict[int, int], now: datetime
    ) -> Percept: ...

    @abstractmethod
    def process(self, percept: Percept) -> list[Any]: ...

    @abstractmethod
    def evaluate(self, prepared: list[Any], percept: Percept) -> list[Evaluation]: ...

    @abstractmethod
    def select(self, evaluations: list[Evaluation], percept: Percept) -> Decision: ...

    def run_cycle(
        self, observations: list[PatientObservation], free_resources: dict[int, int], now: datetime
    ) -> Decision:
        percept = self.perceive(observations, free_resources, now)
        prepared = self.process(percept)
        evaluations = self.evaluate(prepared, percept)
        return self.select(evaluations, percept)
