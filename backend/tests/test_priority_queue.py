"""Gestão dinâmica da fila (serviço + BD)."""
from datetime import timedelta

import pytest
from sqlalchemy import select

from app.models.agent import PriorityHistory, QueueEntry, UtilityScore
from app.models.resource import Resource
from app.schemas.common import ResourceNeedIn, SymptomIn, VitalSignsIn
from app.schemas.patient import PatientCreate, PatientUpdate
from app.services.config_service import ConfigService
from app.services.patient_service import PatientService
from app.services.priority_service import PriorityService


def new(db, clock, code, age=40, sev=5, hr=None, wait=0, needs=()):
    svc = PatientService(db, clock)
    p = svc.create(
        PatientCreate(
            patient_code=code, age=age,
            vital_signs=VitalSignsIn(heart_rate=hr) if hr else None,
            symptoms=[SymptomIn(description="sintoma", simulated_severity=sev)],
            required_resources=list(needs),
            arrived_at=clock.now() - timedelta(minutes=wait),
        )
    )
    PriorityService(db, clock).recalculate("patient_created")
    return p


def codes(db, clock):
    return [i["patient_code"] for i in PriorityService(db, clock).get_queue()["items"]]


def test_insert_orders_by_utility(db, clock):
    new(db, clock, "LOW", sev=2)
    new(db, clock, "HIGH", sev=9, hr=150)
    new(db, clock, "MID", sev=5)
    assert codes(db, clock) == ["HIGH", "MID", "LOW"]


def test_positions_and_history_recorded(db, clock):
    new(db, clock, "A", sev=2)
    b = new(db, clock, "B", sev=9)
    entries = {e.patient_id: e.position for e in db.scalars(select(QueueEntry))}
    assert sorted(entries.values()) == [1, 2]
    hist = db.scalars(select(PriorityHistory).order_by(PriorityHistory.id)).all()
    assert any(h.previous_position is None and h.new_position == 1 for h in hist)  # A entrou
    moved = [h for h in hist if h.patient_id != b.id and h.previous_position == 1 and h.new_position == 2]
    assert moved, "A deve ter descido da posição 1 para 2 quando B chegou"


def test_update_recalculates(db, clock):
    a = new(db, clock, "A", sev=3)
    new(db, clock, "B", sev=6)
    assert codes(db, clock) == ["B", "A"]
    PatientService(db, clock).update(a.id, PatientUpdate(symptoms=[SymptomIn(description="agravou", simulated_severity=10)],
                                                         vital_signs=VitalSignsIn(oxygen_saturation=80, heart_rate=160)))
    PriorityService(db, clock).recalculate("patient_updated")
    assert codes(db, clock) == ["A", "B"]


def test_time_passing_reorders_queue(db, clock):
    new(db, clock, "FRESH", sev=6)
    new(db, clock, "OLD", sev=5.5, wait=0)
    assert codes(db, clock)[0] == "FRESH"
    # só o OLD envelhece: recuamos a sua chegada
    old = db.scalars(select(__import__("app.models.patient", fromlist=["Patient"]).Patient).where(
        __import__("app.models.patient", fromlist=["Patient"]).Patient.patient_code == "OLD")).one()
    old.arrived_at = clock.now() - timedelta(minutes=240)
    db.commit()
    assert codes(db, clock)[0] == "OLD"
    assert db.scalars(select(PriorityHistory).where(PriorityHistory.trigger == "time_elapsed")).first() is not None


def test_get_queue_does_not_write_when_nothing_changes(db, clock):
    new(db, clock, "A", sev=4)
    PriorityService(db, clock).get_queue()
    before = db.scalar(select(__import__("sqlalchemy").func.count(UtilityScore.id)))
    PriorityService(db, clock).get_queue()
    clock.advance(1)
    PriorityService(db, clock).get_queue()
    after = db.scalar(select(__import__("sqlalchemy").func.count(UtilityScore.id)))
    assert before == after


def test_config_change_recomputes_and_versions(db, clock):
    new(db, clock, "NEW-LOW", sev=3, wait=0)
    new(db, clock, "OLD-MID", sev=2, wait=240)
    before = codes(db, clock)
    cfg = ConfigService(db)
    row, warnings = cfg.update({"w1": 5, "w2": 80, "w3": 10, "w4": 5}, None, "espera domina")
    assert row.version == 2 and warnings
    PriorityService(db, clock).recalculate("config_changed", force=True)
    after = codes(db, clock)
    assert after[0] == "OLD-MID"
    assert [r.version for r in cfg.history()] == [2, 1]
    assert cfg.get_active().version == 2
    assert before != after or before[0] == "OLD-MID"


def test_call_next_respects_resources_and_updates_usage(db, clock):
    bed = db.scalars(select(Resource).where(Resource.resource_name == "Cama")).one()
    bed.quantity_available = 1
    db.commit()
    need = [ResourceNeedIn(resource_id=bed.id, quantity=1)]
    new(db, clock, "HIGH-BED", sev=9, hr=150, needs=need)
    new(db, clock, "LOW-BED", sev=4, needs=need)
    new(db, clock, "LOW-NOBED", sev=3)
    svc = PriorityService(db, clock)

    r1 = svc.call_next()
    assert r1["called"] and r1["patient_code"] == "HIGH-BED"
    db.refresh(bed)
    assert bed.quantity_in_use == 1

    r2 = svc.call_next()  # a cama está ocupada: LOW-BED fica à frente mas bloqueado
    assert r2["called"] and r2["patient_code"] == "LOW-NOBED"

    r3 = svc.call_next()
    assert not r3["called"]

    high = PatientService(db, clock).list(status="in_service")
    PatientService(db, clock).update(next(p.id for p in high if p.patient_code == "HIGH-BED"), PatientUpdate(status="attended"))
    db.refresh(bed)
    assert bed.quantity_in_use == 0
    r4 = svc.call_next()
    assert r4["called"] and r4["patient_code"] == "LOW-BED"


def test_leaving_queue_is_logged(db, clock):
    a = new(db, clock, "A", sev=5)
    PatientService(db, clock).update(a.id, PatientUpdate(status="left"))
    PriorityService(db, clock).recalculate("status_changed")
    assert codes(db, clock) == []
    assert db.scalars(select(PriorityHistory).where(PriorityHistory.new_position.is_(None))).first() is not None


def test_ordering_is_deterministic_across_runs(db, clock):
    for i, s in enumerate([5, 5, 5, 7, 3], start=1):
        new(db, clock, f"P{i}", sev=s)
    first = codes(db, clock)
    for _ in range(3):
        assert codes(db, clock) == first


def test_invalid_status_transition_rejected(db, clock):
    from app.core.errors import ConflictError

    a = new(db, clock, "A")
    with pytest.raises(ConflictError):
        PatientService(db, clock).update(a.id, PatientUpdate(status="attended"))
