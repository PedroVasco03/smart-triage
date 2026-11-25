"use client";

import Link from "next/link";
import { useState } from "react";
import { ArrowRightCircle, Clock, RefreshCw, Sparkles } from "lucide-react";
import { PageHeader } from "@/components/page-header";
import { Card } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Table, TBody, TD, TH, THead, TR } from "@/components/ui/table";
import { BandBadge } from "@/components/band-badge";
import { FactorLegend, UtilityBar } from "@/components/utility-bar";
import { InServicePanel } from "@/components/in-service-panel";
import { ResourcesPanel } from "@/components/resources-panel";
import { Empty, ErrorBanner, InfoBanner, LoadingBlock } from "@/components/feedback";
import { useAction, useApi } from "@/hooks/useApi";
import { queueService } from "@/services/queue";
import { simulationService } from "@/services/simulation";
import { fmtAge, fmtMinutes, fmtNumber, fmtTime } from "@/lib/utils";

export default function QueuePage() {
  const queue = useApi(() => queueService.get(), [], 5000);
  const action = useAction();
  const [version, setVersion] = useState(0);
  const [notice, setNotice] = useState<string | null>(null);
  const q = queue.data;

  const refresh = () => {
    queue.reload();
    setVersion((v) => v + 1);
  };

  const run = async (fn: () => Promise<string | void>) => {
    const msg = await action.run(fn);
    if (typeof msg === "string") setNotice(msg);
    refresh();
  };

  return (
    <>
      <PageHeader
        title="Fila de prioridades"
        description="Ordenada pela utilidade que o agente calcula. Reavaliada sempre que o tempo, os dados ou os recursos mudam."
        actions={
          <>
            <Button variant="outline" size="sm" disabled={action.busy} title="Cria pacientes com dados aleatórios (não usa IA)"
              onClick={() => run(async () => {
                const r = await simulationService.generate(8, Math.floor(Math.random() * 100000));
                return `${r.length} pacientes fictícios gerados (dados aleatórios, sem IA).`;
              })}>
              <Sparkles className="h-4 w-4" /> Gerar 8 pacientes fictícios
            </Button>
            <Button variant="outline" size="sm" disabled={action.busy} title="Faz passar o tempo: a espera sobe e os atendimentos em curso avançam"
              onClick={() => run(async () => {
                const r = await simulationService.advanceTime(15);
                return r.services_completed.length
                  ? `Avançaram 15 min. Atendimentos concluídos: ${r.services_completed.join(", ")}.`
                  : "Avançaram 15 min.";
              })}>
              <Clock className="h-4 w-4" /> Avançar 15 min
            </Button>
            <Button variant="outline" size="sm" disabled={action.busy} onClick={() => run(async () => { await queueService.recalculate(); })}>
              <RefreshCw className="h-4 w-4" /> Recalcular
            </Button>
            <Button size="sm" disabled={action.busy || !q || q.items.length === 0}
              onClick={() => run(async () => (await queueService.callNext()).message)}>
              <ArrowRightCircle className="h-4 w-4" /> Chamar próximo
            </Button>
          </>
        }
      />
      <ErrorBanner message={queue.error ?? action.error} />
      {notice && (
        <div role="status" className="mb-4 flex items-start justify-between gap-3 rounded-md border border-brand/30 bg-brand-soft px-3 py-2 text-sm text-brand-dark">
          <span>{notice}</span>
          <button className="text-xs underline" onClick={() => setNotice(null)}>Fechar</button>
        </div>
      )}
      {q && q.items.length > 0 && q.next_patient_id === null && (
        <InfoBanner>
          Ninguém pode ser chamado agora: faltam recursos para todos os pacientes em espera. Conclui um atendimento em
          curso ou aumenta os recursos nos painéis abaixo.
        </InfoBanner>
      )}
      <div className="mb-3 flex flex-wrap items-center justify-between gap-2">
        <FactorLegend />
        {q && <p className="text-xs text-muted">Avaliado às {fmtTime(q.evaluated_at)} · configuração v{q.config_version}</p>}
      </div>
      <Card>
        {!q ? (
          <div className="p-5">{queue.loading ? <LoadingBlock rows={6} /> : null}</div>
        ) : q.items.length === 0 ? (
          <div className="p-5">
            <Empty title="A fila está vazia">
              <Link className="underline" href="/patients/new">Regista um paciente</Link> ou usa “Gerar 8 pacientes fictícios”.
            </Empty>
          </div>
        ) : (
          <Table>
            <THead>
              <TR>
                <TH className="w-12">#</TH><TH>Paciente</TH><TH>Sintomas</TH><TH>Espera</TH><TH className="min-w-[200px]">Utilidade</TH><TH>Prioridade</TH><TH>Notas</TH>
              </TR>
            </THead>
            <TBody>
              {q.items.map((it) => (
                <TR key={it.patient_id} className={it.patient_id === q.next_patient_id ? "bg-brand-soft/60" : undefined}>
                  <TD className="font-semibold">{it.position}</TD>
                  <TD>
                    <Link href={`/queue/${it.patient_id}`} className="font-medium underline-offset-2 hover:underline">{it.patient_code}</Link>
                    <div className="text-xs text-muted">{fmtAge(it.age)}</div>
                  </TD>
                  <TD className="max-w-[220px] truncate text-muted">{it.symptoms.join(", ") || "–"}</TD>
                  <TD>{fmtMinutes(it.waiting_minutes)}</TD>
                  <TD>
                    <div className="flex items-center gap-3">
                      <span className="w-12 text-right font-semibold">{fmtNumber(it.utility_score)}</span>
                      <UtilityBar contributions={it.contributions} className="w-40" />
                    </div>
                  </TD>
                  <TD><BandBadge band={it.band} /></TD>
                  <TD>
                    <div className="flex flex-wrap gap-1">
                      {it.patient_id === q.next_patient_id && <Badge color="#0F766E">Próximo atendível</Badge>}
                      {it.blocked_by_resources && <Badge color="#C28A1B">Sem recursos</Badge>}
                      {it.tie_break_applied && <Badge color="#3B6FB6">Desempate</Badge>}
                    </div>
                  </TD>
                </TR>
              ))}
            </TBody>
          </Table>
        )}
      </Card>

      <div className="mt-6 grid gap-6 lg:grid-cols-2">
        <InServicePanel version={version} onChange={refresh} />
        <ResourcesPanel version={version} onChange={refresh} />
      </div>
    </>
  );
}
