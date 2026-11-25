"""Experiências reproduzíveis para o relatório académico.

Gera tabelas (CSV), gráficos (PNG) e um relatório em Markdown em `reports/`.
Não usa a base de dados: corre o agente e o motor de simulação diretamente.

Uso (dentro de backend/, com o venv ativo):
    python -m scripts.run_experiments                      # experiências completas
    python -m scripts.run_experiments --seeds 1 2 --n 30   # mais rápido
Os resultados descrevem o comportamento do agente; não têm validade clínica.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402

from app.agents.domain import AgentConfig, AgentParams, PatientObservation, ResourceNeed, Weights  # noqa: E402
from app.agents.utility_agent import UtilityAgent  # noqa: E402
from app.simulation.engine import build_population, run_simulation  # noqa: E402
from app.simulation.scenarios import SCENARIOS  # noqa: E402

NOW = datetime(2026, 1, 1, 12, 0, 0)
BALANCED = Weights(40, 20, 30, 10)
WEIGHT_SETS = {
    "Equilibrado 40/20/30/10": Weights(40, 20, 30, 10),
    "Gravidade 70/5/20/5": Weights(70, 5, 20, 5),
    "Espera 10/70/15/5": Weights(10, 70, 15, 5),
}
COLORS = {"G": "#B4412F", "E": "#3B6FB6", "R": "#C28A1B", "A": "#5B7F6A", "U": "#12202B"}

NORMAL = {"temperature": 36.8, "heart_rate": 75, "oxygen_saturation": 98, "respiratory_rate": 16,
          "systolic_pressure": 120, "diastolic_pressure": 78}
SEVERE = {"temperature": 39.5, "heart_rate": 140, "oxygen_saturation": 86, "respiratory_rate": 30,
          "systolic_pressure": 85, "diastolic_pressure": 55}
MODERATE = {"temperature": 38.2, "heart_rate": 105, "oxygen_saturation": 94, "respiratory_rate": 22,
            "systolic_pressure": 132, "diastolic_pressure": 84}


def obs(pid: int, age: int, wait: float, vitals: dict, sev: float, needs=()) -> PatientObservation:
    return PatientObservation(
        patient_id=pid, patient_code=f"P{pid}", age=age, arrived_at=NOW - timedelta(minutes=wait),
        vitals=dict(vitals), symptom_severities=(sev,), needs=tuple(needs),
    )


def evaluate(observations, weights: Weights = BALANCED, free: Optional[dict] = None, params: Optional[AgentParams] = None):
    agent = UtilityAgent(AgentConfig(1, weights, params or AgentParams()))
    return agent.run_cycle(observations, free or {}, NOW)


def mix(a: dict, b: dict, t: float) -> dict:
    return {k: round(a[k] + (b[k] - a[k]) * t, 2) for k in a}


# --------------------------------------------------------------------------- experiências
def exp_waiting() -> pd.DataFrame:
    rows = []
    for t in range(0, 301, 5):
        ev = evaluate([obs(1, 40, t, MODERATE, 5)]).ranking[0]
        rows.append({"espera_min": t, "E": ev.factors.E, "U": ev.utility, "contrib_E": ev.contributions["E"]})
    return pd.DataFrame(rows)


def exp_gravity() -> pd.DataFrame:
    rows = []
    for s in np.arange(0, 10.01, 0.5):
        ev = evaluate([obs(1, 40, 0, mix(NORMAL, SEVERE, s / 10), float(s))]).ranking[0]
        rows.append({"severidade_simulada": float(s), "G": ev.factors.G, "R": ev.factors.R, "U": ev.utility})
    return pd.DataFrame(rows)


def exp_risk() -> pd.DataFrame:
    rows = []
    for age in range(0, 96, 5):
        ev = evaluate([obs(1, age, 0, MODERATE, 5)]).ranking[0]
        rows.append({"idade": age, "fator_idade": ev.factors.age_factor, "R": ev.factors.R, "U": ev.utility})
    return pd.DataFrame(rows)


def exp_resources() -> pd.DataFrame:
    need = (ResourceNeed(1, "Cama", 4),)
    profiles = {"gravidade/risco baixos": (30, NORMAL, 1.0), "gravidade/risco altos": (80, SEVERE, 9.0)}
    rows = []
    for name, (age, vit, sev) in profiles.items():
        for free in range(0, 5):
            ev = evaluate([obs(1, age, 0, vit, sev, need)], free={1: free}).ranking[0]
            rows.append({"perfil": name, "unidades_livres_de_4": free, "A_raw": ev.factors.A_raw, "A": ev.factors.A, "U": ev.utility})
    return pd.DataFrame(rows)


def crossover_minutes(weights: Weights) -> Optional[int]:
    """Espera mínima (min) para um paciente leve antigo ultrapassar um grave que acabou de chegar."""
    severe_new = obs(1, 60, 0, SEVERE, 8.5)
    for t in range(0, 3001):
        mild_old = obs(2, 35, t, mix(NORMAL, MODERATE, 0.15), 2.0)
        if evaluate([severe_new, mild_old], weights).ranking[0].patient_id == 2:
            return t
    return None


def exp_crossover() -> pd.DataFrame:
    rows = []
    for w2 in (5, 10, 20, 30, 40, 50, 60, 70):
        rest = 100 - w2
        w = Weights(rest * 0.45, w2, rest * 0.40, rest * 0.15)
        rows.append({"peso_espera_%": w2, "peso_gravidade_%": round(w.normalized().w1 * 100, 1), "espera_para_ultrapassar_min": crossover_minutes(w)})
    return pd.DataFrame(rows)


def exp_scenarios(seeds: list[int], n: int, duration: int) -> tuple[pd.DataFrame, pd.DataFrame]:
    raw = []
    for key, sc in SCENARIOS.items():
        for wname, w in WEIGHT_SETS.items():
            for seed in seeds:
                pop = build_population(np.random.default_rng(seed), sc, n, float(duration), sc.default_capacity)
                res = run_simulation(UtilityAgent(AgentConfig(1, w)), pop, sc.default_capacity, float(duration), NOW)
                m = res.metrics
                raw.append({
                    "cenario": key, "pesos": wname, "seed": seed, "atendidos": m["served"], "n": m["n_patients"],
                    "espera_media": m["avg_wait_minutes"], "espera_alta": m["avg_wait_high_severity"],
                    "espera_baixa": m["avg_wait_low_severity"], "espera_max": m["max_wait_minutes"],
                })
    df = pd.DataFrame(raw)
    agg = df.groupby(["cenario", "pesos"], sort=False).agg(
        atendidos=("atendidos", "mean"), espera_media=("espera_media", "mean"), espera_alta=("espera_alta", "mean"),
        espera_baixa=("espera_baixa", "mean"), espera_max=("espera_max", "mean"),
    ).round(1).reset_index()
    return df, agg


def check_determinism(n: int, duration: int) -> bool:
    sc = SCENARIOS["mixed_flow"]
    runs = []
    for _ in range(2):
        pop = build_population(np.random.default_rng(99), sc, n, float(duration), sc.default_capacity)
        runs.append(run_simulation(UtilityAgent(AgentConfig(1, BALANCED)), pop, sc.default_capacity, float(duration), NOW).metrics)
    return runs[0] == runs[1]


# --------------------------------------------------------------------------- gráficos
def _style(ax, xlabel, ylabel, title):
    ax.set_xlabel(xlabel)
    ax.set_ylabel(ylabel)
    ax.set_title(title, fontsize=11, loc="left")
    ax.grid(axis="y", color="#E4E9E8")
    for s in ("top", "right"):
        ax.spines[s].set_visible(False)


def plot_all(out: Path, e1, e2, e3, e4, e5, agg) -> None:
    fig, ax = plt.subplots(figsize=(6.4, 3.8))
    ax.plot(e1["espera_min"], e1["E"], color=COLORS["E"], label="E (fator de espera)")
    ax.plot(e1["espera_min"], e1["U"], color=COLORS["U"], label="U (utilidade)")
    ax.legend(frameon=False)
    _style(ax, "Tempo de espera (min)", "Pontos (0-100)", "E1. Espera: crescimento que satura")
    fig.tight_layout(); fig.savefig(out / "e1_espera.png", dpi=150); plt.close(fig)

    fig, ax = plt.subplots(figsize=(6.4, 3.8))
    ax.plot(e2["severidade_simulada"], e2["G"], color=COLORS["G"], label="G")
    ax.plot(e2["severidade_simulada"], e2["R"], color=COLORS["R"], label="R")
    ax.plot(e2["severidade_simulada"], e2["U"], color=COLORS["U"], label="U")
    ax.legend(frameon=False)
    _style(ax, "Gravidade simulada (0-10, com sinais vitais proporcionais)", "Pontos (0-100)", "E2. Influência da gravidade")
    fig.tight_layout(); fig.savefig(out / "e2_gravidade.png", dpi=150); plt.close(fig)

    fig, ax = plt.subplots(figsize=(6.4, 3.8))
    ax.plot(e3["idade"], e3["R"], color=COLORS["R"], label="R")
    ax.plot(e3["idade"], e3["U"], color=COLORS["U"], label="U")
    ax.legend(frameon=False)
    _style(ax, "Idade (anos)", "Pontos (0-100)", "E3. Risco de agravamento e idade (forma de U)")
    fig.tight_layout(); fig.savefig(out / "e3_risco_idade.png", dpi=150); plt.close(fig)

    fig, ax = plt.subplots(figsize=(6.4, 3.8))
    for name, g in e4.groupby("perfil"):
        ax.plot(g["A_raw"], g["A"], marker="o", label=name)
    ax.plot([0, 100], [0, 100], color="#999", linestyle=":", label="sem proteção")
    ax.legend(frameon=False)
    _style(ax, "Recursos disponíveis antes da proteção (A_raw)", "A (após proteção)", "E4. A falta de recursos penaliza menos quem está em risco")
    fig.tight_layout(); fig.savefig(out / "e4_recursos.png", dpi=150); plt.close(fig)

    fig, ax = plt.subplots(figsize=(6.4, 3.8))
    ok = e5.dropna(subset=["espera_para_ultrapassar_min"])
    ax.plot(ok["peso_espera_%"], ok["espera_para_ultrapassar_min"], marker="o", color=COLORS["E"])
    _style(ax, "Peso da espera (%)", "Espera necessária (min)", "E5. Quando a espera ultrapassa a gravidade")
    fig.tight_layout(); fig.savefig(out / "e5_cruzamento.png", dpi=150); plt.close(fig)

    scen = list(agg["cenario"].unique())
    sets = list(agg["pesos"].unique())
    fig, ax = plt.subplots(figsize=(8, 4))
    width = 0.8 / len(sets)
    palette = ["#0F766E", "#B4412F", "#3B6FB6"]
    for i, s in enumerate(sets):
        vals = [agg[(agg["cenario"] == c) & (agg["pesos"] == s)]["espera_alta"].iloc[0] for c in scen]
        ax.bar(np.arange(len(scen)) + i * width, vals, width, label=s, color=palette[i % 3])
    ax.set_xticks(np.arange(len(scen)) + width)
    ax.set_xticklabels(scen, rotation=15, ha="right", fontsize=8)
    ax.legend(frameon=False, fontsize=8)
    _style(ax, "", "Espera média (min)", "E6. Espera média dos casos de gravidade alta, por cenário e pesos")
    fig.tight_layout(); fig.savefig(out / "e6_cenarios.png", dpi=150); plt.close(fig)


# --------------------------------------------------------------------------- relatório
def md_table(df: pd.DataFrame, digits: int = 1) -> str:
    def f(v):
        if v is None or (isinstance(v, float) and np.isnan(v)):
            return "n/d"
        return f"{v:.{digits}f}" if isinstance(v, float) else str(v)

    head = "| " + " | ".join(df.columns) + " |\n|" + "---|" * len(df.columns) + "\n"
    return head + "\n".join("| " + " | ".join(f(v) for v in row) + " |" for row in df.itertuples(index=False)) + "\n"


def build_report(e1, e2, e3, e4, e5, raw, agg, deterministic: bool, args) -> str:
    e60 = e1[e1["espera_min"] == 60].iloc[0]
    e300 = e1[e1["espera_min"] == 300].iloc[0]
    g0, g10 = e2.iloc[0], e2.iloc[-1]
    r_young, r_mid, r_old = e3[e3["idade"] == 0].iloc[0], e3[e3["idade"] == 35].iloc[0], e3[e3["idade"] == 90].iloc[0]
    low0 = e4[(e4["perfil"] == "gravidade/risco baixos") & (e4["unidades_livres_de_4"] == 0)].iloc[0]
    high0 = e4[(e4["perfil"] == "gravidade/risco altos") & (e4["unidades_livres_de_4"] == 0)].iloc[0]
    c20 = e5[e5["peso_espera_%"] == 20]["espera_para_ultrapassar_min"].iloc[0]
    c60 = e5[e5["peso_espera_%"] == 60]["espera_para_ultrapassar_min"].iloc[0]
    def cross_sentence(w2: int, v) -> str:
        if v is None or pd.isna(v):
            return f"com o peso da espera a {w2}% o paciente leve nunca ultrapassa o grave (testado até 3000 min)"
        return f"com o peso da espera a {w2}% o paciente leve ultrapassa o grave após {int(v)} min"

    def mean_delta(pesos_prefix: str, col: str) -> Optional[float]:
        base = agg[agg["pesos"].str.startswith("Equilibrado")].set_index("cenario")[col]
        other = agg[agg["pesos"].str.startswith(pesos_prefix)].set_index("cenario")[col]
        d = (other - base).dropna()
        return float(d.mean()) if len(d) else None

    def signed(v: Optional[float]) -> str:
        return "n/d" if v is None else f"{v:+.1f} min"

    d_esp_alta, d_esp_baixa = mean_delta("Espera", "espera_alta"), mean_delta("Espera", "espera_baixa")
    d_gra_alta, d_gra_baixa = mean_delta("Gravidade", "espera_alta"), mean_delta("Gravidade", "espera_baixa")
    reading = (
        f"Face ao perfil equilibrado, e em média nos cenários com dados: o perfil «Espera» altera a espera dos casos de "
        f"gravidade alta em {signed(d_esp_alta)} e a dos de gravidade baixa em {signed(d_esp_baixa)}; o perfil «Gravidade» altera-as em "
        f"{signed(d_gra_alta)} e {signed(d_gra_baixa)}."
    )
    if d_esp_alta is not None and d_gra_alta is not None and abs(d_gra_alta) < abs(d_esp_alta) / 2:
        reading += (
            " Os pesos de referência já são dominados pela gravidade, por isso reforçá-los muda pouco; o que altera "
            "os resultados é dar à espera um peso comparável ao da gravidade (ver E5)."
        )

    return f"""# Relatório de experiências do agente baseado em utilidade

Gerado por `python -m scripts.run_experiments` (seeds {args.seeds}, {args.n} pacientes por simulação, {args.duration} min).
Todos os dados são sintéticos e os parâmetros são experimentais: **estes resultados descrevem o comportamento do agente
e não constituem validação clínica.**

Função: `U = (w1·G + w2·E + w3·R + w4·A) / Σw`, pesos de referência 40/20/30/10.

## E1. Como a pontuação muda quando o tempo de espera aumenta

Paciente de referência (40 anos, sinais moderados, sintoma 5/10), espera de 0 a 300 min.

![E1](e1_espera.png)

Com τ = 60 min, uma hora de espera dá E = {e60['E']:.1f} e a utilidade passa a {e60['U']:.1f}; aos 300 min, E = {e300['E']:.1f}
(satura abaixo de 100). Como w2 = 20%, a espera contribui no máximo com 20 pontos.

## E2. Como a gravidade influencia a utilidade

Varia-se a severidade simulada de 0 a 10 com sinais vitais proporcionais (normais → críticos).

![E2](e2_gravidade.png)

G sobe de {g0['G']:.1f} para {g10['G']:.1f} e U de {g0['U']:.1f} para {g10['U']:.1f}. A gravidade também alimenta R, por isso o efeito
total sobre U é maior do que o do peso w1 isolado.

## E3. Como o risco de agravamento influencia a ordenação

Mesmos sinais e sintomas, idades de 0 a 95 anos.

![E3](e3_risco_idade.png)

R = {r_young['R']:.1f} aos 0 anos, {r_mid['R']:.1f} aos 35 e {r_old['R']:.1f} aos 90: crianças pequenas e idosos sobem na fila
em relação a adultos com os mesmos sinais (U = {r_young['U']:.1f} / {r_mid['U']:.1f} / {r_old['U']:.1f}).

## E4. Como os recursos afetam as decisões

Paciente que precisa de 4 unidades; 0 a 4 livres. Compara-se um perfil de baixo risco com um de alto risco.

![E4](e4_recursos.png)

{md_table(e4, 1)}
Sem nenhuma unidade livre, o perfil de baixo risco fica com A = {low0['A']:.1f} e o de alto risco com A = {high0['A']:.1f}:
a proteção impede que a falta de recursos reduza a prioridade de quem está em risco.

## E5. Quando a espera ultrapassa a gravidade (sensibilidade aos pesos)

Um paciente leve que espera há t minutos contra um paciente grave que acabou de chegar. Mostra-se a espera necessária
para o leve passar à frente, em função do peso da espera.

![E5](e5_cruzamento.png)

{md_table(e5, 0)}
{cross_sentence(20, c20).capitalize()} (referência); {cross_sentence(60, c60)}.
Este é o mecanismo que impede a espera isolada de superar a gravidade, e que o ecrã do agente sinaliza quando w2 ≥ w1.

## E6. Cenários e configurações de pesos

Média de {len(args.seeds)} seed(s). Esperas em minutos de tempo simulado.

![E6](e6_cenarios.png)

{md_table(agg, 1)}
{reading}
"n/d" significa que o cenário não tem pacientes desse grupo de gravidade (por exemplo, `similar_scores` só tem casos moderados).

## Reprodutibilidade

Mesma seed e mesma configuração produzem exatamente as mesmas métricas: **{'confirmado' if deterministic else 'FALHOU'}**.
"""


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default="reports")
    ap.add_argument("--seeds", type=int, nargs="+", default=[1, 2, 3, 4, 5])
    ap.add_argument("--n", type=int, default=40)
    ap.add_argument("--duration", type=int, default=480)
    args = ap.parse_args()

    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)

    e1, e2, e3, e4, e5 = exp_waiting(), exp_gravity(), exp_risk(), exp_resources(), exp_crossover()
    raw, agg = exp_scenarios(args.seeds, args.n, args.duration)
    deterministic = check_determinism(args.n, args.duration)

    for name, df in (("e1_espera", e1), ("e2_gravidade", e2), ("e3_risco_idade", e3), ("e4_recursos", e4),
                     ("e5_cruzamento", e5), ("e6_cenarios_bruto", raw), ("e6_cenarios_resumo", agg)):
        df.to_csv(out / f"{name}.csv", index=False)
    plot_all(out, e1, e2, e3, e4, e5, agg)
    (out / "RELATORIO_EXPERIENCIAS.md").write_text(build_report(e1, e2, e3, e4, e5, raw, agg, deterministic, args), encoding="utf-8")
    print(f"Relatório em {out}/RELATORIO_EXPERIENCIAS.md")


if __name__ == "__main__":
    main()
