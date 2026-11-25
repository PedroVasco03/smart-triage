"use client";

import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Table, TBody, TD, TH, THead, TR } from "@/components/ui/table";
import { LoadingBlock } from "@/components/feedback";
import { SimTimelineChart } from "@/components/charts/charts";
import { useApi } from "@/hooks/useApi";
import { simulationService } from "@/services/simulation";
import { fmtMinutes, fmtNumber } from "@/lib/utils";
import type { SimMetrics, SimSession } from "@/types";

export function MetricGrid({ m }: { m: SimMetrics }) {
  const items: [string, string][] = [
    ["Atendidos", `${m.served} de ${m.n_patients}`],
    ["Ainda em espera no fim", String(m.unserved)],
    ["Espera média", fmtMinutes(m.avg_wait_minutes)],
    ["Espera máxima", fmtMinutes(m.max_wait_minutes)],
    ["Espera média, gravidade alta", fmtMinutes(m.avg_wait_high_severity)],
    ["Espera média, gravidade baixa", fmtMinutes(m.avg_wait_low_severity)],
    ["Utilidade média ao ser chamado", fmtNumber(m.avg_utility_at_service)],
    ["Percentil 90 da espera", fmtMinutes(m.p90_wait_minutes)],
  ];
  return (
    <div className="grid grid-cols-2 gap-3 lg:grid-cols-4">
      {items.map(([label, value]) => (
        <div key={label} className="rounded-md border border-line bg-white p-3">
          <p className="text-xs text-muted">{label}</p>
          <p className="mt-0.5 text-lg font-semibold">{value}</p>
        </div>
      ))}
    </div>
  );
}

export function SessionView({ session }: { session: SimSession }) {
  const results = useApi(() => simulationService.results(session.id), [session.id]);
  const m = session.summary?.metrics;
  const cfg = session.configuration;
  return (
    <div className="space-y-6">
      <Card>
        <CardHeader>
          <CardTitle>{session.session_name}</CardTitle>
          <CardDescription>
            Cenário {cfg.scenario} · {cfg.n_patients} pacientes · {cfg.duration_minutes} min · seed {cfg.seed} · pesos G/E/R/A:{" "}
            {["w1", "w2", "w3", "w4"].map((k) => fmtNumber((cfg.normalized_weights?.[k] ?? 0) * 100, 0)).join(" / ")} · capacidade:{" "}
            {Object.entries(cfg.capacity ?? {}).map(([k, v]) => `${k} ${v}`).join(", ")}
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          {m && <MetricGrid m={m} />}
          {m && (
            <p className="text-xs text-muted">
              Utilização dos recursos: {Object.entries(m.resource_utilization).map(([k, v]) => `${k} ${fmtNumber(v * 100, 0)}%`).join(" · ")}
            </p>
          )}
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>Evolução da fila</CardTitle>
          <CardDescription>Tamanho da fila e utilidade média dos pacientes em espera, ao longo do tempo simulado.</CardDescription>
        </CardHeader>
        <CardContent>
          {session.summary?.timeline?.length ? <SimTimelineChart points={session.summary.timeline} /> : null}
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>Decisões por paciente</CardTitle>
          <CardDescription>Ordem em que o agente chamou cada paciente e porquê. Os que não foram chamados mostram a última avaliação.</CardDescription>
        </CardHeader>
        <CardContent>
          {!results.data ? <LoadingBlock rows={4} /> : (
            <Table>
              <THead>
                <TR><TH>Ordem</TH><TH>Paciente</TH><TH>Perfil</TH><TH>Espera</TH><TH>Utilidade</TH><TH>Explicação</TH></TR>
              </THead>
              <TBody>
                {results.data.map((r) => (
                  <TR key={r.id}>
                    <TD className="font-semibold">{r.assigned_position ?? "–"}</TD>
                    <TD>{r.patient_code}</TD>
                    <TD className="text-muted">{r.details?.profile ?? "–"}</TD>
                    <TD>{fmtMinutes(r.waiting_minutes)}</TD>
                    <TD className="font-semibold">{fmtNumber(r.utility_score)}</TD>
                    <TD className="max-w-[420px] text-xs text-muted">
                      <details>
                        <summary className="cursor-pointer text-ink">Ver explicação</summary>
                        <p className="mt-1 leading-relaxed">{r.decision_explanation}</p>
                        <p className="mt-1">{r.details?.evaluated_when}</p>
                      </details>
                    </TD>
                  </TR>
                ))}
              </TBody>
            </Table>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
