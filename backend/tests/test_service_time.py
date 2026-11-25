"""Duração do atendimento: os recursos ocupados voltam sozinhos quando o atendimento termina."""
from sqlalchemy import create_engine, text, select

from app.database.init_db import ensure_columns
from app.models.agent import PriorityHistory
from app.models.resource import Resource

PATIENT = {"patient_code": "S-1", "age": 40, "symptoms": [{"description": "sintoma", "simulated_severity": 5}]}


def _bed(client):
    return next(r for r in client.get("/resources").json() if r["resource_name"] == "Cama")


def _register(client, code, bed_id, minutes=30):
    r = client.post("/patients", json={**PATIENT, "patient_code": code, "service_minutes": minutes,
                                       "required_resources": [{"resource_id": bed_id, "quantity": 1}]})
    assert r.status_code == 201, r.text
    return r.json()


def test_service_ends_by_itself_and_frees_resources(client, clock):
    bed = _bed(client)
    client.put(f"/resources/{bed['id']}", json={"quantity_available": 1})
    a = _register(client, "S-A", bed["id"], 30)
    _register(client, "S-B", bed["id"], 30)

    assert client.post("/queue/call-next").json()["patient_code"] == "S-A"
    assert client.post("/queue/call-next").json()["called"] is False  # a única cama está ocupada
    assert _bed(client)["quantity_free"] == 0
    p = client.get(f"/patients/{a['id']}").json()
    assert p["status"] == "in_service" and 29 <= p["service_remaining_minutes"] <= 30

    clock.advance(31)
    client.get("/queue")  # a leitura da fila conclui o atendimento
    assert client.get(f"/patients/{a['id']}").json()["status"] == "attended"
    assert _bed(client)["quantity_free"] == 1
    assert client.post("/queue/call-next").json()["patient_code"] == "S-B"


def test_advance_time_finishes_services_in_progress(client):
    bed = _bed(client)
    a = _register(client, "S-C", bed["id"], 20)
    client.post("/queue/call-next")
    r = client.post("/simulation/advance-time", json={"minutes": 25}).json()
    assert r["services_completed"] == ["S-C"]
    assert client.get(f"/patients/{a['id']}").json()["status"] == "attended"
    assert _bed(client)["quantity_in_use"] == 0


def test_without_duration_service_stays_until_manual_finish(client, clock):
    bed = _bed(client)
    a = client.post("/patients", json={**PATIENT, "patient_code": "S-D",
                                       "required_resources": [{"resource_id": bed["id"], "quantity": 1}]}).json()
    assert a["service_minutes"] is None
    client.post("/queue/call-next")
    clock.advance(600)
    client.get("/queue")
    assert client.get(f"/patients/{a['id']}").json()["status"] == "in_service"
    assert client.put(f"/patients/{a['id']}", json={"status": "attended"}).status_code == 200
    assert _bed(client)["quantity_in_use"] == 0


def test_completion_is_logged_in_history(client, db, clock):
    bed = _bed(client)
    _register(client, "S-E", bed["id"], 10)
    client.post("/queue/call-next")
    clock.advance(11)
    client.get("/queue")
    reasons = [h.reason for h in db.scalars(select(PriorityHistory))]
    assert any("Atendimento concluído após 10 min" in r for r in reasons)


def test_duration_is_validated(client):
    assert client.post("/patients", json={**PATIENT, "patient_code": "S-F", "service_minutes": 0}).status_code == 422
    assert client.post("/patients", json={**PATIENT, "patient_code": "S-G", "service_minutes": 5000}).status_code == 422


def test_generated_patients_have_duration(client):
    r = client.post("/simulation/generate", json={"n": 5, "seed": 2}).json()
    assert all(p["service_minutes"] and p["service_minutes"] >= 5 for p in r)


def test_resources_can_be_created_and_raised(client):
    r = client.post("/resources", json={"resource_name": "Ventilador", "quantity_available": 2})
    assert r.status_code == 201 and r.json()["quantity_free"] == 2
    assert client.post("/resources", json={"resource_name": "Ventilador", "quantity_available": 1}).status_code == 409
    assert client.put(f"/resources/{r.json()['id']}", json={"quantity_available": 5}).json()["quantity_free"] == 5


def test_ensure_columns_upgrades_old_database(tmp_path):
    eng = create_engine(f"sqlite:///{tmp_path/'old.db'}")
    with eng.begin() as c:
        c.execute(text("CREATE TABLE patients (id INTEGER PRIMARY KEY, patient_code VARCHAR(32))"))
    assert ensure_columns(eng) == ["patients.service_minutes"]
    assert ensure_columns(eng) == []  # idempotente
