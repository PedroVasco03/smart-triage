"""Relógio injetável.

O tempo de espera depende do "agora". Para a ordenação ser determinística e testável,
o agente nunca chama datetime.now(): recebe sempre o instante de avaliação.
Todos os datetimes são UTC "naive" (sem tzinfo) para compatibilidade com MySQL.
"""
from datetime import datetime, timedelta, timezone
from typing import Callable, Protocol


def utcnow() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


class Clock(Protocol):
    def now(self) -> datetime: ...


class SystemClock:
    def now(self) -> datetime:
        return utcnow()


class FixedClock:
    """Relógio controlável (testes e demonstrações)."""

    def __init__(self, start: datetime):
        self._now = start

    def now(self) -> datetime:
        return self._now

    def set(self, value: datetime) -> None:
        self._now = value

    def advance(self, minutes: float) -> None:
        self._now = self._now + timedelta(minutes=minutes)


class VirtualClock:
    """Relógio da simulação: base + minutos simulados fornecidos por uma função."""

    def __init__(self, start: datetime, minutes_fn: Callable[[], float]):
        self._start = start
        self._minutes_fn = minutes_fn

    def now(self) -> datetime:
        return self._start + timedelta(minutes=float(self._minutes_fn()))
