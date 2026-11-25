"""Garante que o script de experiências corre e que as conclusões que o relatório afirma se verificam."""
from argparse import Namespace

from scripts import run_experiments as ex


def test_waiting_curve_is_monotonic_and_bounded():
    df = ex.exp_waiting()
    assert df["E"].is_monotonic_increasing and df["E"].max() < 100
    assert df["contrib_E"].max() <= 20.0 + 1e-9


def test_gravity_and_risk_curves():
    g = ex.exp_gravity()
    assert g["G"].is_monotonic_increasing and g["U"].iloc[-1] > g["U"].iloc[0]
    r = ex.exp_risk()
    assert r["R"].iloc[0] > r["R"].iloc[7]  # 0 anos > 35 anos
    assert r["R"].iloc[-1] > r["R"].iloc[7]  # 95 anos > 35 anos


def test_resource_protection_shows_in_experiment():
    df = ex.exp_resources()
    low = df[(df["perfil"] == "gravidade/risco baixos") & (df["unidades_livres_de_4"] == 0)]["A"].iloc[0]
    high = df[(df["perfil"] == "gravidade/risco altos") & (df["unidades_livres_de_4"] == 0)]["A"].iloc[0]
    assert high > low + 50


def test_crossover_decreases_as_waiting_weight_grows():
    df = ex.exp_crossover().dropna()
    values = list(df["espera_para_ultrapassar_min"])
    assert values == sorted(values, reverse=True) and len(values) >= 2


def test_scenarios_and_determinism_and_report(tmp_path):
    raw, agg = ex.exp_scenarios([1], 12, 120)
    assert set(agg["cenario"]) == set(ex.SCENARIOS) and len(agg) == len(ex.SCENARIOS) * len(ex.WEIGHT_SETS)
    assert ex.check_determinism(12, 120)
    e1, e2, e3, e4, e5 = ex.exp_waiting(), ex.exp_gravity(), ex.exp_risk(), ex.exp_resources(), ex.exp_crossover()
    ex.plot_all(tmp_path, e1, e2, e3, e4, e5, agg)
    text = ex.build_report(e1, e2, e3, e4, e5, raw, agg, True, Namespace(seeds=[1], n=12, duration=120))
    assert "confirmado" in text and (tmp_path / "e6_cenarios.png").exists()
