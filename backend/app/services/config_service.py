"""Configurações versionadas do agente (pesos e parâmetros)."""
from __future__ import annotations

import copy
from typing import Any, Optional

from sqlalchemy import func, select, update
from sqlalchemy.orm import Session

from app.agents.domain import AgentConfig, AgentParams, Weights
from app.core.errors import ValidationFailure
from app.models.agent import AgentConfiguration


class ConfigService:
    def __init__(self, db: Session):
        self.db = db

    def get_active(self) -> AgentConfiguration:
        row = self.db.scalars(select(AgentConfiguration).where(AgentConfiguration.is_active.is_(True))).first()
        if row is None:
            row = AgentConfiguration(
                version=1,
                weights=Weights().to_dict(),
                params=AgentParams().to_dict(),
                is_active=True,
                note="Configuração inicial (parâmetros experimentais)",
            )
            self.db.add(row)
            self.db.commit()
        return row

    @staticmethod
    def to_domain(row: AgentConfiguration) -> AgentConfig:
        return AgentConfig(version=row.version, weights=Weights.from_dict(row.weights), params=AgentParams.from_dict(row.params))

    def history(self) -> list[AgentConfiguration]:
        return list(self.db.scalars(select(AgentConfiguration).order_by(AgentConfiguration.version.desc())))

    def update(
        self, weights: Optional[dict[str, float]], params: Optional[dict[str, Any]], note: Optional[str]
    ) -> tuple[AgentConfiguration, list[str]]:
        current = self.get_active()
        new_weights = Weights.from_dict({**current.weights, **(weights or {})})
        try:
            warnings = new_weights.validate()
        except ValueError as e:
            raise ValidationFailure(str(e)) from e

        merged = copy.deepcopy(current.params)
        for key, value in (params or {}).items():
            if value is None:
                continue
            if key == "vital_ranges":
                for vk, vr in value.items():
                    merged.setdefault("vital_ranges", {}).setdefault(vk, {}).update(
                        {k: v for k, v in vr.items() if v is not None}
                    )
            else:
                merged[key] = value
        try:
            normalized_params = AgentParams.from_dict(merged).to_dict()
        except (TypeError, ValueError) as e:
            raise ValidationFailure(f"Parâmetros inválidos: {e}") from e

        next_version = (self.db.scalar(select(func.max(AgentConfiguration.version))) or 0) + 1
        self.db.execute(update(AgentConfiguration).values(is_active=False))
        row = AgentConfiguration(
            version=next_version,
            weights=new_weights.to_dict(),
            params=normalized_params,
            is_active=True,
            note=note,
        )
        self.db.add(row)
        self.db.commit()
        return row, warnings

    @staticmethod
    def to_out(row: AgentConfiguration) -> dict[str, Any]:
        w = Weights.from_dict(row.weights)
        try:
            warnings = w.validate()
        except ValueError:
            warnings = []
        return {
            "id": row.id,
            "version": row.version,
            "is_active": row.is_active,
            "weights": w.to_dict(),
            "normalized_weights": w.normalized().to_dict(),
            "params": row.params,
            "note": row.note,
            "warnings": warnings,
            "created_at": row.created_at,
        }
