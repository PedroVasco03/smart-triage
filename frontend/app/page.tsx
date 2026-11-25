"use client";

import Link from "next/link";
import { PageHeader } from "@/components/page-header";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { ErrorBanner, LoadingBlock, Empty } from "@/components/feedback";
import { DistributionChart, QueueEvolutionChart } from "@/components/charts/charts";
import { useApi } from "@/hooks/useApi";
import { statisticsService } from "@/services/statistics";
import { TRIGGER_LABELS } from "@/lib/constants";
import { fmtDateTime, fmtNumber } from "@/lib/utils";

function Stat({ label, value, hint }: { label: string; value: string | number; hint?: string }) {
  return (
    <Card>
      <CardContent className="pt-5">
        <p className="text-sm text-muted">{label}</p>
        <p className="mt-1 text-3xl font-semibold">{value}</p>
        {hint && <p className="mt-1 text-xs text-muted">{hint}</p>}
      </CardContent>
    </Card>
  );
}

export default function DashboardPage() {
  const dash = useApi(() => statisticsService.dashboard(), [], 8000);
  const evo = useApi(() => statisticsService.evolution({ limit: 60 }), [], 8000);
  const d = dash.data;

  return (
    <>
      <PageHeader
        title="Painel"
        description="Visão geral da fila e do comportamento do agente. Os valores atualizam-se sozinhos."
        actions={
          <Button asChild variant="outline"><Link href="/patients/new">Registar paciente</Link></Button>
        }
      />
      <ErrorBanner message={dash.error} />
      {!d ? (
        dash.loading ? <LoadingBlock rows={5} /> : null
      ) : (
        <div className="space-y-6">
          <div className="grid grid-cols-2 gap-4 lg:grid-cols-5">
            <Stat label="Pacientes registados" value={d.total_patients} />
            <Stat label="Na fila" value={d.in_queue} />
            <Stat label="Em atendimento" value={d.in_service} />
            <Stat label="Atendidos" value={d.attended} />
            <Stat label="Utilidade média" value={fmtNumber(d.average_utility)} hint={`Configuração v${d.config_version}`} />
          </div>

          <div className="grid gap-6 lg:grid-cols-2">
            <Card>
              <CardHeader>
                <CardTitle>Distribuição das prioridades simuladas</CardTitle>
                <CardDescription>Pacientes na fila por faixa de utilidade.</CardDescription>
              </CardHeader>
              <CardContent>
                {d.in_queue === 0 ? <Empty title="Fila vazia">Regista um paciente ou gera pacientes fictícios na Simulação.</Empty> : <DistributionChart data={d.distribution} />}
              </CardContent>
            </Card>
            <Card>
              <CardHeader>
                <CardTitle>Evolução da utilidade</CardTitle>
                <CardDescription>Média e máximo da fila em cada reavaliação.</CardDescription>
              </CardHeader>
              <CardContent>
                {evo.data && evo.data.points.length > 1 ? (
                  <QueueEvolutionChart points={evo.data.points} />
                ) : (
                  <Empty title="Ainda sem histórico suficiente">A evolução aparece depois de algumas reavaliações da fila.</Empty>
                )}
              </CardContent>
            </Card>
          </div>

          <Card>
            <CardHeader>
              <CardTitle>Atividade recente</CardTitle>
              <CardDescription>Últimas alterações de posição decididas pelo agente.</CardDescription>
            </CardHeader>
            <CardContent>
              {d.recent_activity.length === 0 ? (
                <p className="text-sm text-muted">Sem atividade ainda.</p>
              ) : (
                <ul className="divide-y divide-line">
                  {d.recent_activity.map((a, i) => (
                    <li key={i} className="flex flex-wrap items-baseline justify-between gap-2 py-2.5 text-sm">
                      <span>
                        <span className="font-medium">{a.patient_code ?? "–"}</span>{" "}
                        <span className="text-muted">{a.reason}</span>
                      </span>
                      <span className="text-xs text-muted">
                        {TRIGGER_LABELS[a.trigger] ?? a.trigger} · {fmtDateTime(a.changed_at)}
                      </span>
                    </li>
                  ))}
                </ul>
              )}
            </CardContent>
          </Card>
        </div>
      )}
    </>
  );
}
