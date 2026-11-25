"""Teste de integração real com MySQL. Só corre se TEST_MYSQL_URL estiver definido, por exemplo:

  export TEST_MYSQL_URL="mysql+pymysql://triage_user:SENHA@127.0.0.1:3306/smart_triage_test"
  pytest tests/test_integration_mysql.py -v

ATENÇÃO: as tabelas da base de teste são apagadas e recriadas. Usa uma base dedicada.
"""
import os

import pytest

pytestmark = pytest.mark.skipif(not os.environ.get("TEST_MYSQL_URL"), reason="TEST_MYSQL_URL não definido")


def test_full_flow_on_mysql(client):
    r = client.post("/patients", json={"patient_code": "MY-1", "age": 50, "symptoms": [{"description": "sintoma", "simulated_severity": 7}]})
    assert r.status_code == 201
    q = client.get("/queue").json()
    assert q["items"][0]["patient_code"] == "MY-1"
    assert client.post("/simulation/start", json={"scenario": "mixed_flow", "n_patients": 20, "seed": 1}).status_code == 201
    assert client.get("/statistics/dashboard").status_code == 200
