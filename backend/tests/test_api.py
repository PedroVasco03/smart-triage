"""Testes de integração da API (FastAPI + SQLAlchemy). Corre em SQLite; usa MySQL se TEST_MYSQL_URL existir."""
PATIENT = {
    "patient_code": "p-001", "age": 67, "sex": "M",
    "vital_signs": {"temperature": 38.9, "heart_rate": 118, "oxygen_saturation": 91,
                    "respiratory_rate": 24, "systolic_pressure": 100, "diastolic_pressure": 60},
    "symptoms": [{"description": "dispneia", "simulated_severity": 8}],
    "required_resources": [],
}


def create(client, code, **kw):
    body = {**PATIENT, "patient_code": code, **kw}
    r = client.post("/patients", json=body)
    assert r.status_code == 201, r.text
    return r.json()


def test_health(client):
    assert client.get("/health").json()["status"] == "ok"


def test_create_get_update_delete_patient(client):
    p = create(client, "P-001")
    assert p["patient_code"] == "P-001" and p["queue_position"] == 1 and p["status"] == "waiting"
    assert client.get(f"/patients/{p['id']}").json()["age"] == 67
    r = client.put(f"/patients/{p['id']}", json={"age": 70, "vital_signs": {"heart_rate": 140}})
    assert r.status_code == 200 and r.json()["age"] == 70 and r.json()["vital_signs"]["heart_rate"] == 140
    assert client.delete(f"/patients/{p['id']}").status_code == 204
    assert client.get(f"/patients/{p['id']}").status_code == 404
    assert client.get("/queue").json()["items"] == []


def test_validation_errors_use_common_format(client):
    r = client.post("/patients", json={**PATIENT, "age": 200})
    assert r.status_code == 422 and r.json()["error"]["code"] == "validation_error"
    r = client.post("/patients", json={**PATIENT, "vital_signs": {"oxygen_saturation": 120}})
    assert r.status_code == 422
    r = client.post("/patients", json={**PATIENT, "vital_signs": {"systolic_pressure": 70, "diastolic_pressure": 90}})
    assert r.status_code == 422


def test_duplicate_code_conflict(client):
    create(client, "DUP-1")
    r = client.post("/patients", json={**PATIENT, "patient_code": "dup-1"})
    assert r.status_code == 409 and r.json()["error"]["code"] == "conflict"


def test_unknown_resource_rejected(client):
    r = client.post("/patients", json={**PATIENT, "patient_code": "R-1", "required_resources": [{"resource_id": 999, "quantity": 1}]})
    assert r.status_code == 422


def test_queue_order_and_detail_explanation(client):
    create(client, "LOW", symptoms=[{"description": "tosse", "simulated_severity": 1}], vital_signs=None, age=30)
    high = create(client, "HIGH")
    q = client.get("/queue").json()
    assert [i["patient_code"] for i in q["items"]] == ["HIGH", "LOW"]
    d = client.get(f"/queue/{high['id']}").json()
    ev = d["evaluation"]
    assert d["live"] and ev["position"] == 1
    assert set(ev["factors"]) >= {"G", "E", "R", "A"}
    assert abs(sum(ev["contributions"].values()) - ev["utility"]) < 0.01
    assert abs(sum(ev["weights"].values()) - 1.0) < 1e-6
    assert "gravidade" in ev["explanation"]


def test_call_next_and_finish_flow(client):
    a = create(client, "A-1")
    r = client.post("/queue/call-next").json()
    assert r["called"] and r["patient_code"] == "A-1"
    assert client.get("/queue").json()["items"] == []
    detail = client.get(f"/queue/{a['id']}").json()  # já fora da fila: última avaliação guardada
    assert detail["live"] is False and detail["in_queue"] is False
    assert client.put(f"/patients/{a['id']}", json={"status": "attended"}).json()["status"] == "attended"
    assert client.put(f"/patients/{a['id']}", json={"status": "waiting"}).status_code == 409


def test_configuration_update_recalculates_and_keeps_history(client):
    create(client, "LOW-OLD", symptoms=[{"description": "sintoma", "simulated_severity": 1}], vital_signs=None, age=30, arrived_at="2026-11-14T06:00:00")
    create(client, "MID-NEW", symptoms=[{"description": "sintoma", "simulated_severity": 7}], vital_signs=None, age=30)
    assert client.get("/queue").json()["items"][0]["patient_code"] == "MID-NEW"
    r = client.put("/agent/configuration", json={"weights": {"w1": 5, "w2": 85, "w3": 5, "w4": 5}, "note": "teste"})
    assert r.status_code == 200 and r.json()["version"] == 2 and r.json()["warnings"]
    assert client.get("/queue").json()["items"][0]["patient_code"] == "LOW-OLD"
    hist = client.get("/agent/configuration/history").json()
    assert [h["version"] for h in hist] == [2, 1] and hist[0]["is_active"] and not hist[1]["is_active"]
    assert client.put("/agent/configuration", json={"weights": {"w1": 0, "w2": 0, "w3": 0, "w4": 0}}).status_code == 422
    assert client.put("/agent/configuration", json={"weights": {"w1": -1}}).status_code == 422


def test_evaluate_what_if_does_not_persist(client):
    body = {"hypothetical": [
        {"label": "grave", "age": 80, "waiting_minutes": 0, "symptoms": [{"description": "sintoma", "simulated_severity": 9}], "vital_signs": {"oxygen_saturation": 85}},
        {"label": "leve", "age": 25, "waiting_minutes": 300, "symptoms": [{"description": "sintoma", "simulated_severity": 1}]},
    ]}
    r = client.post("/agent/evaluate", json=body)
    assert r.status_code == 200
    evs = r.json()["evaluations"]
    assert evs[0]["patient_code"].startswith("grave")
    assert client.get("/queue").json()["items"] == []
    r2 = client.post("/agent/evaluate", json={**body, "weights_override": {"w1": 1, "w2": 98, "w3": 1, "w4": 0}})
    assert r2.json()["evaluations"][0]["patient_code"].startswith("leve")


def test_resources_change_triggers_recalc_and_blocks(client):
    res = client.get("/resources").json()
    bed = next(r for r in res if r["resource_name"] == "Cama")
    create(client, "NEEDBED", required_resources=[{"resource_id": bed["id"], "quantity": 1}])
    assert client.get("/queue").json()["items"][0]["blocked_by_resources"] is False
    assert client.put(f"/resources/{bed['id']}", json={"quantity_available": 0}).status_code == 200
    assert client.get("/queue").json()["items"][0]["blocked_by_resources"] is True
    assert client.post("/queue/call-next").json()["called"] is False


def test_generate_and_advance_time(client):
    r = client.post("/simulation/generate", json={"n": 6, "seed": 3, "max_wait_minutes": 20})
    assert r.status_code == 201 and len(r.json()) == 6
    q1 = client.get("/queue").json()
    waits1 = {i["patient_code"]: i["waiting_minutes"] for i in q1["items"]}
    assert client.post("/simulation/advance-time", json={"minutes": 60}).json()["patients_affected"] == 6
    q2 = client.get("/queue").json()
    assert all(i["waiting_minutes"] >= waits1[i["patient_code"]] + 59.9 for i in q2["items"])
    assert [i["position"] for i in q2["items"]] == list(range(1, 7))


def test_queue_history_endpoint(client):
    create(client, "H1")
    create(client, "H2", symptoms=[{"description": "sintoma", "simulated_severity": 10}])
    h = client.get("/queue/history").json()
    assert h and {"previous_position", "new_position", "reason", "trigger"} <= set(h[0])


def test_statistics_endpoints(client):
    create(client, "S1")
    create(client, "S2", symptoms=[{"description": "sintoma", "simulated_severity": 2}], vital_signs=None, age=30)
    d = client.get("/statistics/dashboard").json()
    assert d["total_patients"] == 2 and d["in_queue"] == 2 and d["average_utility"] is not None
    assert sum(b["count"] for b in d["distribution"]) == 2 and d["recent_activity"]
    assert client.get("/statistics/priority-distribution").json()["total"] == 2
    evo = client.get("/statistics/utility-evolution").json()
    assert evo["points"] and "avg_utility" in evo["points"][0]
    assert client.get("/statistics/utility-evolution", params={"patient_id": 1}).json()["points"]
    st = client.get("/agent/status").json()
    assert st["queue_size"] == 2 and st["config_version"] == 1


def test_simulation_start_results_and_determinism(client):
    body = {"scenario": "severe_vs_waiting", "n_patients": 24, "duration_minutes": 360, "seed": 7}
    s1 = client.post("/simulation/start", json=body)
    assert s1.status_code == 201, s1.text
    s2 = client.post("/simulation/start", json=body)
    m1, m2 = s1.json()["summary"]["metrics"], s2.json()["summary"]["metrics"]
    assert m1 == m2 and m1["n_patients"] == 24
    sid = s1.json()["id"]
    res = client.get(f"/simulation/sessions/{sid}/results").json()
    assert len(res) == 24 and res[0]["assigned_position"] == 1
    assert res[0]["decision_explanation"]
    assert len(client.get("/simulation/sessions").json()) == 2
    assert client.get("/simulation/sessions/9999").status_code == 404
    # as sessões não poluem a fila real
    assert client.get("/patients").json() == []
    assert client.get("/queue").json()["items"] == []


def test_simulation_compare_weights_changes_outcomes(client):
    body = {
        "scenario": "severe_vs_waiting", "n_patients": 30, "duration_minutes": 480, "seed": 11,
        "weight_sets": [
            {"name": "gravidade", "weights": {"w1": 70, "w2": 5, "w3": 20, "w4": 5}},
            {"name": "espera", "weights": {"w1": 5, "w2": 80, "w3": 10, "w4": 5}},
        ],
    }
    r = client.post("/simulation/compare", json=body)
    assert r.status_code == 200
    a, b = r.json()["runs"]
    assert a["metrics"]["avg_wait_high_severity"] < b["metrics"]["avg_wait_high_severity"]


def test_unknown_scenario_and_bad_weights(client):
    assert client.post("/simulation/start", json={"scenario": "nope"}).status_code == 422
    assert client.post("/simulation/start", json={"weights_override": {"w1": 0, "w2": 0, "w3": 0, "w4": 0}}).status_code == 422


def test_scenarios_listed(client):
    keys = {s["key"] for s in client.get("/simulation/scenarios").json()}
    assert {"mixed_flow", "severe_vs_waiting", "deterioration_risk", "similar_scores", "limited_resources"} <= keys


def test_timezone_aware_arrival_is_normalized(client):
    p = create(client, "TZ-1", arrived_at="2026-11-14T09:00:00Z")
    assert abs(p["waiting_minutes"] - 60) < 0.1
    q = client.get("/queue").json()
    assert abs(q["items"][0]["waiting_minutes"] - 60) < 0.1
