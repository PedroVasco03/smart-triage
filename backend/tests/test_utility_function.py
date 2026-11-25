"""Testes unitários da função de utilidade (puros, sem BD)."""
from datetime import datetime, timedelta

import pytest

from app.agents.domain import AgentConfig, AgentParams, PatientObservation, ResourceNeed, Weights
from app.agents.utility_agent import UtilityAgent
from app.services import utility_service as us

NOW = datetime(2026, 11, 14, 10, 0)
P = AgentParams()


def obs(pid, age=40, wait=0.0, vitals=None, sev=(), needs=()):
    return PatientObservation(
        patient_id=pid, patient_code=f"P{pid}", age=age, arrived_at=NOW - timedelta(minutes=wait),
        vitals=vitals or {}, symptom_severities=tuple(sev), needs=tuple(needs),
    )


def run(observations, free=None, weights=None):
    agent = UtilityAgent(AgentConfig(1, weights or Weights()))
    return agent.run_cycle(observations, free or {}, NOW)


# --- normalização -----------------------------------------------------------------
def test_vital_deviation_inside_range_is_zero():
    assert us.vital_deviation(80, P.vital_ranges["heart_rate"]) == 0.0


def test_vital_deviation_scales_linearly_and_saturates():
    rng = P.vital_ranges["heart_rate"]  # máx 100, tol_high 50
    assert us.vital_deviation(125, rng) == pytest.approx(50.0)
    assert us.vital_deviation(300, rng) == 100.0
    assert us.vital_deviation(50, rng) == pytest.approx(50.0)  # mín 60, tol_low 20


def test_waiting_score_is_monotonic_and_saturates_below_100():
    values = [us.waiting_score(t, 60) for t in (0, 10, 60, 240, 100000)]
    assert values == sorted(values)
    assert values[0] == 0.0
    assert all(v <= 100.0 for v in values)
    assert us.waiting_score(60, 60) == pytest.approx(63.21, abs=0.01)


def test_age_factor_is_u_shaped():
    assert us.age_factor(0, P) == 100.0
    assert us.age_factor(30, P) == 0.0
    assert us.age_factor(90, P) == 100.0
    assert 0 < us.age_factor(75, P) < 100


def test_all_factors_stay_in_0_100():
    f = us.compute_factors(
        obs(1, age=0, wait=1e6, vitals={"temperature": 44, "heart_rate": 240, "oxygen_saturation": 55,
                                         "respiratory_rate": 60, "systolic_pressure": 55, "diastolic_pressure": 35}, sev=(10,)),
        NOW, {}, P,
    )
    for x in (f.G, f.E, f.R, f.A):
        assert 0.0 <= x <= 100.0


# --- fórmula e pesos --------------------------------------------------------------
def test_utility_is_weighted_sum_and_contributions_add_up():
    d = run([obs(1, age=70, wait=30, vitals={"heart_rate": 130, "oxygen_saturation": 90}, sev=(7,))])
    ev = d.ranking[0]
    assert sum(ev.contributions.values()) == pytest.approx(ev.utility)
    w = ev.weights
    expected = w["w1"] * ev.factors.G + w["w2"] * ev.factors.E + w["w3"] * ev.factors.R + w["w4"] * ev.factors.A
    assert ev.utility == pytest.approx(expected)


def test_weights_are_normalized_by_sum():
    a = run([obs(1, sev=(8,), wait=20)], weights=Weights(40, 20, 30, 10)).ranking[0].utility
    b = run([obs(1, sev=(8,), wait=20)], weights=Weights(0.4, 0.2, 0.3, 0.1)).ranking[0].utility
    assert a == pytest.approx(b)


def test_invalid_weights_rejected():
    with pytest.raises(ValueError):
        Weights(-1, 20, 30, 10).validate()
    with pytest.raises(ValueError):
        Weights(0, 0, 0, 0).validate()
    assert Weights(10, 30, 30, 30).validate()  # aviso: espera >= gravidade


def test_gravity_dominates_when_wait_cannot_close_the_gap():
    """Com os pesos por defeito, a espera contribui no máximo 20 pts: não compensa uma diferença
    grande de gravidade (>= 50 pontos de G)."""
    severe_new = obs(1, vitals={"heart_rate": 150, "oxygen_saturation": 85, "respiratory_rate": 32,
                                "temperature": 40, "systolic_pressure": 60}, sev=(10,), wait=0)
    mild_old = obs(2, vitals={"heart_rate": 75}, sev=(1,), wait=100000)
    d = run([mild_old, severe_new])
    assert d.ranking[0].patient_id == 1


def test_waiting_time_raises_priority_between_similar_patients():
    young = obs(1, sev=(5,), vitals={"heart_rate": 105}, wait=0)
    old = obs(2, sev=(5,), vitals={"heart_rate": 105}, wait=90)
    assert run([young, old]).ranking[0].patient_id == 2


def test_utility_increases_with_waiting_time():
    u = [run([obs(1, sev=(5,), wait=t)]).ranking[0].utility for t in (0, 15, 60, 180)]
    assert u == sorted(u) and u[0] < u[-1]


def test_risk_of_deterioration_influences_order():
    same = dict(sev=(4,), vitals={"heart_rate": 90}, wait=10)
    baby = obs(1, age=1, **same)
    adult = obs(2, age=35, **same)
    d = run([adult, baby])
    assert d.ranking[0].patient_id == 1
    assert d.ranking[0].factors.R > d.ranking[1].factors.R


# --- recursos ---------------------------------------------------------------------
def test_missing_resources_penalize_low_risk_more_than_high_risk():
    need = (ResourceNeed(1, "Cama", 1),)
    low = us.compute_factors(obs(1, sev=(1,), needs=need), NOW, {1: 0}, P)
    high = us.compute_factors(obs(2, age=85, sev=(10,), vitals={"oxygen_saturation": 80, "heart_rate": 160}, needs=need), NOW, {1: 0}, P)
    assert low.A_raw == high.A_raw == 0.0
    assert low.A <= 10.0 + 1e-9
    assert high.A > 80  # protegido pelo risco/gravidade


def test_select_skips_blocked_patient_and_picks_next_feasible():
    need_bed = (ResourceNeed(1, "Cama", 1),)
    top = obs(1, sev=(10,), vitals={"heart_rate": 160, "oxygen_saturation": 80}, needs=need_bed)
    other = obs(2, sev=(3,))
    d = run([other, top], free={1: 0})
    assert d.ranking[0].patient_id == 1  # a prioridade não desce por falta de recursos
    assert d.next_patient_id == 2  # mas quem é atendido a seguir respeita os recursos
    assert d.blocked[0].patient_id == 1


def test_no_resources_for_anyone_returns_no_next():
    need = (ResourceNeed(1, "Cama", 1),)
    d = run([obs(1, needs=need), obs(2, needs=need)], free={1: 0})
    assert d.next_patient_id is None


# --- determinismo e desempate -----------------------------------------------------
def test_ties_are_resolved_deterministically():
    a = obs(5, sev=(5,), wait=10)
    b = obs(3, sev=(5,), wait=10)
    d1 = run([a, b])
    d2 = run([b, a])
    assert [e.patient_id for e in d1.ranking] == [e.patient_id for e in d2.ranking] == [3, 5]
    assert all(e.tie_break_applied for e in d1.ranking)


def test_same_input_same_output():
    population = [obs(i, age=20 + i * 7, wait=i * 9, sev=(i % 10,), vitals={"heart_rate": 70 + i * 6}) for i in range(1, 25)]
    r1 = [(e.patient_id, round(e.utility, 9)) for e in run(population).ranking]
    r2 = [(e.patient_id, round(e.utility, 9)) for e in run(list(reversed(population))).ranking]
    assert r1 == r2


def test_top_k_matches_full_sort():
    agent = UtilityAgent(AgentConfig(1))
    population = [obs(i, age=20 + i * 3, wait=i * 4, sev=(i % 10,)) for i in range(1, 30)]
    d = agent.run_cycle(population, {}, NOW)
    top = agent.top_k(d.ranking, 5)
    assert [e.patient_id for e in top] == [e.patient_id for e in d.ranking[:5]]


def test_missing_data_is_handled():
    d = run([obs(1), obs(2, sev=(6,))])
    e1 = next(e for e in d.ranking if e.patient_id == 1)
    assert e1.factors.G == 0.0 and e1.factors.notes


def test_explanation_lists_every_factor():
    ev = run([obs(1, age=80, sev=(7,), wait=25, vitals={"oxygen_saturation": 90})]).ranking[0]
    for word in ("gravidade", "risco de agravamento", "tempo de espera", "recursos", "não é uma classificação clínica"):
        assert word in ev.explanation
