"use client";

import Link from "next/link";
import { useParams } from "next/navigation";
import { ArrowLeft } from "lucide-react";
import { PageHeader } from "@/components/page-header";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Table, TBody, TD, TH, THead, TR } from "@/components/ui/table";
import { BandBadge } from "@/components/band-badge";
import { FactorLegend, UtilityBar } from "@/components/utility-bar";
import { PatientEvolutionChart } from "@/components/charts/charts";
import { Empty, ErrorBanner, InfoBanner, LoadingBlock } from "@/components/feedback";
import { useApi } from "@/hooks/useApi";
import { queueService } from "@/services/queue";
import { statisticsService } from "@/services/statistics";
import { FACTORS, STATUS_LABELS, TRIGGER_LABELS, VITAL_FIELDS } from "@/lib/constants";
import { fmtAge, fmtDateTime, fmtNumber } from "@/lib/utils";

export default function DecisionDetailPage() {
  const params = useParams<{ id: string }>();
  const id = Number(params.id);
  const detail = useApi(() => queueService.detail(id), [id], 5000);
  const evo = useApi(() => statisticsService.evolution({ patient_id: id, limit: 80 }), [id], 8000);
  const history = useApi(() => queueService.history({ patient_id: id, limit: 20 }), [id], 8000);

  const d = detail.data;
  const ev = d?.evaluation;

  return (
    <>
      <PageHeader
        title={d ? `Decisão do agente: ${d.patient_code}` : "Decisão do agente"}
        description="Como o agente chegou a esta pontuação: fatores, pesos e contributo de cada um."
        actions={<Button asChild variant="outline" size="sm"><Link href="/queue"><ArrowLeft className="h-4 w-4" /> Voltar à fila</Link></Button>}
      />
      <ErrorBanner message={detail.error} />
      {!d || !ev ? (
        detail.loading ? <LoadingBlock rows={5} /> : null
      ) : (
        <div className="space-y-6">
          {!d.live && (
            <InfoBanner>
              Este paciente já não está na fila ({STATUS_LABELS[d.status] ?? d.status}). Mostra-se a última avaliação guardada,
              de {fmtDateTime(d.evaluated_at)}.
            </InfoBanner>
          )}
          {d.blocked_by_resources && (
            <InfoBanner>
              Faltam recursos: {d.missing_resources.map((m) => `${m.name} (precisa ${m.needed}, livre ${m.free})`).join("; ")}.
              A prioridade não desce por isso, mas o paciente só é chamado quando houver recursos.
            </InfoBanner>
          )}

          <Card>
            <CardContent className="pt-5">
              <div className="flex flex-wrap items-end justify-between gap-4">
                <div>
                  <p className="text-sm text-muted">Pontuação de utilidade</p>
                  <p className="text-5xl font-semibold leading-none">{fmtNumber(ev.utility)}<span className="ml-1 text-lg font-normal text-muted">/ 100</span></p>
                </div>
                <div className="flex flex-wrap items-center gap-2">
                  {d.in_queue && <Badge>Posição {ev.position}</Badge>}
                  <BandBadge band={ev.band} />
                  {ev.tie_break_applied && <Badge color="#3B6FB6">Desempate aplicado</Badge>}
                  <Badge>{fmtAge(d.age)}</Badge>
                </div>
              </div>
              <UtilityBar contributions={ev.contributions} className="mt-5" height={16} />
              <div className="mt-2"><FactorLegend /></div>
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle>Contributo de cada fator</CardTitle>
              <CardDescription>Utilidade = soma de (peso × fator). Os fatores estão normalizados entre 0 e 100.</CardDescription>
            </CardHeader>
            <CardContent>
              <Table>
                <THead>
                  <TR><TH>Fator</TH><TH>Valor (0–100)</TH><TH>Peso</TH><TH>Contributo (pts)</TH><TH>O que mede</TH></TR>
                </THead>
                <TBody>
                  {FACTORS.map((f) => (
                    <TR key={f.key}>
                      <TD>
                        <span className="mr-2 inline-block h-2.5 w-2.5 rounded-sm align-middle" style={{ backgroundColor: f.color }} />
                        <span className="font-medium">{f.label}</span>
                      </TD>
                      <TD>{fmtNumber(ev.factors[f.key])}</TD>
                      <TD>{fmtNumber(ev.weights[f.weightKey] * 100, 0)}%</TD>
                      <TD className="font-semibold">{fmtNumber(ev.contributions[f.key])}</TD>
                      <TD className="text-muted">{f.hint}</TD>
                    </TR>
                  ))}
                  <TR>
                    <TD className="font-semibold">Total</TD><TD /><TD>100%</TD><TD className="font-semibold">{fmtNumber(ev.utility)}</TD><TD />
                  </TR>
                </TBody>
              </Table>
              <p className="mt-4 rounded-md bg-paper p-3 text-sm leading-relaxed">{ev.explanation}</p>
            </CardContent>
          </Card>

          <div className="grid gap-6 lg:grid-cols-2">
            <Card>
              <CardHeader>
                <CardTitle>Sinais vitais e desvios</CardTitle>
                <CardDescription>Desvio 0 = dentro do intervalo de referência experimental; 100 = muito fora.</CardDescription>
              </CardHeader>
              <CardContent>
                {!d.vital_signs ? (
                  <Empty title="Sem sinais vitais registados">A gravidade usou só os sintomas.</Empty>
                ) : (
                  <Table>
                    <THead><TR><TH>Sinal</TH><TH>Valor</TH><TH className="w-40">Desvio</TH></TR></THead>
                    <TBody>
                      {VITAL_FIELDS.filter((f) => d.vital_signs?.[f.key] != null).map((f) => {
                        const dev = ev.factors.deviations[f.key] ?? 0;
                        return (
                          <TR key={f.key}>
                            <TD>{f.label}</TD>
                            <TD>{d.vital_signs?.[f.key]} {f.unit}</TD>
                            <TD>
                              <div className="flex items-center gap-2">
                                <div className="h-2 flex-1 overflow-hidden rounded-sm bg-line/70">
                                  <div className="h-full bg-factor-g" style={{ width: `${dev}%` }} />
                                </div>
                                <span className="w-9 text-right text-xs">{fmtNumber(dev, 0)}</span>
                              </div>
                            </TD>
                          </TR>
                        );
                      })}
                    </TBody>
                  </Table>
                )}
                <div className="mt-4 space-y-1 text-sm text-muted">
                  <p>Sintomas: {d.symptoms.length ? d.symptoms.map((s) => `${s.description} (${s.simulated_severity})`).join(", ") : "nenhum"}</p>
                  <p>Intermédios: V = {ev.factors.V === null ? "–" : fmtNumber(ev.factors.V)} · S = {fmtNumber(ev.factors.S)} · pior desvio = {fmtNumber(ev.factors.max_deviation)} · fator de idade = {fmtNumber(ev.factors.age_factor)} · recursos antes da proteção = {fmtNumber(ev.factors.A_raw)}</p>
                  {ev.factors.notes.map((n, i) => <p key={i}>{n}</p>)}
                </div>
              </CardContent>
            </Card>

            <Card>
              <CardHeader>
                <CardTitle>Evolução desta pontuação</CardTitle>
                <CardDescription>Utilidade e fatores em cada reavaliação guardada.</CardDescription>
              </CardHeader>
              <CardContent>
                {evo.data && evo.data.points.length > 1 ? <PatientEvolutionChart points={evo.data.points} /> : <Empty title="Ainda sem histórico suficiente" />}
              </CardContent>
            </Card>
          </div>

          <Card>
            <CardHeader>
              <CardTitle>Histórico de posição</CardTitle>
              <CardDescription>Cada linha é uma decisão registada para auditoria.</CardDescription>
            </CardHeader>
            <CardContent>
              {!history.data || history.data.length === 0 ? (
                <p className="text-sm text-muted">Sem alterações registadas.</p>
              ) : (
                <ul className="divide-y divide-line text-sm">
                  {history.data.map((h) => (
                    <li key={h.id} className="flex flex-wrap items-baseline justify-between gap-2 py-2.5">
                      <span>{h.reason}</span>
                      <span className="text-xs text-muted">{TRIGGER_LABELS[h.trigger] ?? h.trigger} · {fmtDateTime(h.changed_at)}</span>
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
