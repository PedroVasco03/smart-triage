from __future__ import annotations

from typing import Any, Optional

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.clock import Clock
from app.models.agent import UtilityScore
from app.models.patient import Patient
from app.services.priority_service import PriorityService


class StatisticsService:
    def __init__(self, db: Session, clock: Clock):
        self.db = db
        self.clock = clock
        self.priority = PriorityService(db, clock)

    def _count(self, *conds) -> int:
        return self.db.scalar(select(func.count(Patient.id)).where(Patient.session_id.is_(None), *conds)) or 0

    def distribution(self, queue: Optional[dict[str, Any]] = None) -> dict[str, Any]:
        queue = queue or self.priority.get_queue()
        bands = self.priority.configs.get_active().params.get("priority_bands", [])
        labels = [str(b[0]) for b in sorted(bands, key=lambda b: -float(b[1]))]
        counts = {label: 0 for label in labels}
        for it in queue["items"]:
            counts[it["band"]] = counts.get(it["band"], 0) + 1
        return {"total": len(queue["items"]), "bands": [{"band": k, "count": v} for k, v in counts.items()]}

    def dashboard(self) -> dict[str, Any]:
        queue = self.priority.get_queue()
        items = queue["items"]
        avg = round(sum(i["utility_score"] for i in items) / len(items), 2) if items else None
        recent = self.priority.history(limit=10)
        return {
            "total_patients": self._count(),
            "in_queue": len(items),
            "in_service": self._count(Patient.status == "in_service"),
            "attended": self._count(Patient.status == "attended"),
            "average_utility": avg,
            "config_version": queue["config_version"],
            "distribution": self.distribution(queue)["bands"],
            "recent_activity": [
                {"patient_code": h["patient_code"], "trigger": h["trigger"], "reason": h["reason"], "changed_at": h["changed_at"]}
                for h in recent
            ],
        }

    def utility_evolution(self, patient_id: Optional[int] = None, limit: int = 200) -> dict[str, Any]:
        if patient_id:
            rows = list(
                self.db.scalars(
                    select(UtilityScore).where(UtilityScore.patient_id == patient_id)
                    .order_by(UtilityScore.calculated_at.desc(), UtilityScore.id.desc()).limit(limit)
                )
            )[::-1]
            pts = [
                {"t": r.calculated_at, "utility": round(r.utility_score, 2), "G": round(r.severity_score, 2),
                 "E": round(r.waiting_time_score, 2), "R": round(r.deterioration_risk_score, 2), "A": round(r.resource_score, 2)}
                for r in rows
            ]
        else:
            stmt = (
                select(UtilityScore.calculated_at, func.avg(UtilityScore.utility_score),
                       func.max(UtilityScore.utility_score), func.count(UtilityScore.id))
                .group_by(UtilityScore.calculated_at).order_by(UtilityScore.calculated_at.desc()).limit(limit)
            )
            pts = [
                {"t": t, "avg_utility": round(float(a), 2), "max_utility": round(float(m), 2), "n": int(n)}
                for t, a, m, n in list(self.db.execute(stmt))[::-1]
            ]
        return {"patient_id": patient_id, "points": pts}
