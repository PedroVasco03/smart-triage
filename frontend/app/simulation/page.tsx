"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { FlaskConical, Play } from "lucide-react";
import { PageHeader } from "@/components/page-header";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input, Label, Select } from "@/components/ui/input";
import { Table, TBody, TD, TH, THead, TR } from "@/components/ui/table";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Empty, ErrorBanner, InfoBanner, LoadingBlock } from "@/components/feedback";
import { CompareChart } from "@/components/charts/charts";
import { MetricGrid, SessionView } from "@/components/session-view";
import { useAction, useApi } from "@/hooks/useApi";
import { simulationService } from "@/services/simulation";
import { fmtDateTime, fmtMinutes, fmtNumber } from "@/lib/utils";
import type { CompareResponse, SimSession, Weights } from "@/types";

const WEIGHT_PRESETS: Record<string, { label: string; w: Weights | null }> = {
  active: { label: "Configuração ativa do agente", w: null },
  balanced: { label: "Equilibrado (40/20/30/10)", w: { w1: 40, w2: 20, w3: 30, w4: 10 } },
  severity: { label: "Gravidade primeiro (70/5/20/5)", w: { w1: 70, w2: 5, w3: 20, w4: 5 } },
  waiting: { label: "Espera primeiro (10/70/15/5)", w: { w1: 10, w2: 70, w3: 15, w4: 5 } },
};

const COMPARE_SETS = [
  { name: "Equilibrado", weights: { w1: 40, w2: 20, w3: 30, w4: 10 } },
  { name: "Gravidade", weights: { w1: 70, w2: 5, w3: 20, w4: 5 } },
  { name: "Espera", weights: { w1: 10, w2: 70, w3: 15, w4: 5 } },
];

export default function SimulationPage() {
  const scenarios = useApi(() => simulationService.scenarios(), []);
  const sessions = useApi(() => simulationService.sessions(), []);
  const action = useAction();

  const [tab, setTab] = useState("run");
  const [scenario, setScenario] = useState("mixed_flow");
  const [n, setN] = useState("40");
  const [duration, setDuration] = useState("480");
  const [seed, setSeed] = useState("42");
  const [preset, setPreset] = useState("active");
  const [capacity, setCapacity] = useState<Record<string, string>>({});
  const [session, setSession] = useState<SimSession | null>(null);
  const [compare, setCompare] = useState<CompareResponse | null>(null);

  const [genN, setGenN] = useState("8");
  const [advance, setAdvance] = useState("30");
  const [liveMsg, setLiveMsg] = useState<string | null>(null);

  const sc = scenarios.data?.find((s) => s.key === scenario);
  useEffect(() => {
    if (sc) setCapacity(Object.fromEntries(Object.entries(sc.default_capacity).map(([k, v]) => [k, String(v)])));
  }, [sc?.key]); // eslint-disable-line react-hooks/exhaustive-deps

  const common = () => ({
    scenario,
    n_patients: Math.max(Number(n) || 1, 1),
    duration_minutes: Math.max(Number(duration) || 30, 30),
    seed: Math.max(Number(seed) || 0, 0),
    capacity: Object.fromEntries(Object.entries(capacity).map(([k, v]) => [k, Math.max(Number(v) || 0, 0)])),
  });

  const run = async () => {
    const res = await action.run(() =>
      simulationService.start({ ...common(), weights_override: WEIGHT_PRESETS[preset].w ?? undefined, session_name: `${sc?.name ?? scenario} · ${WEIGHT_PRESETS[preset].label}` }),
    );
    if (res) {
      setSession(res);
      sessions.reload();
    }
  };

  const runCompare = async () => {
    const res = await action.run(() => simulationService.compare({ ...common(), weight_sets: COMPARE_SETS }));
    if (res) {
      setCompare(res);
      sessions.reload();
    }
  };

  const openSession = async (id: number) => {
    const res = await action.run(() => simulationService.session(id));
    if (res) {
      setSession(res);
      setTab("run");
    }
  };

  const generate = async () => {
    const res = await action.run(() => simulationService.generate(Math.max(Number(genN) || 1, 1), Math.floor(Math.random() * 100000)));
    if (res) setLiveMsg(`${res.length} paciente(s) fictício(s) adicionados à fila.`);
  };
  const advanceTime = async () => {
    const res = await action.run(() => simulationService.advanceTime(Math.max(Number(advance) || 1, 1)));
    if (res) setLiveMsg(`Tempo avançado ${res.advanced_minutes} min para ${res.patients_affected} paciente(s) em espera.${res.services_completed.length ? ` Atendimentos concluídos: ${res.services_completed.join(", ")}.` : ""}`);
  };

  return (
    <>
      <PageHeader
        title="Simulação"
        description="Testa o agente em cenários sintéticos reproduzíveis. Os resultados são experimentais e não têm validade clínica."
      />
      <ErrorBanner message={action.error} />

      <Tabs value={tab} onValueChange={setTab}>
        <TabsList>
          <TabsTrigger value="run">Executar cenário</TabsTrigger>
          <TabsTrigger value="compare">Comparar pesos</TabsTrigger>
          <TabsTrigger value="live">Fila ao vivo</TabsTrigger>
          <TabsTrigger value="history">Resultados anteriores</TabsTrigger>
        </TabsList>

        <div className="mt-4">
          <Card>
            <CardHeader>
              <CardTitle>Parâmetros do cenário</CardTitle>
              <CardDescription>{sc?.description ?? "A carregar cenários…"}</CardDescription>
            </CardHeader>
            <CardContent className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
              <div className="space-y-1.5 sm:col-span-2">
                <Label htmlFor="scenario">Cenário</Label>
                <Select id="scenario" value={scenario} onChange={(e) => setScenario(e.target.value)}>
                  {(scenarios.data ?? []).map((s) => <option key={s.key} value={s.key}>{s.name}</option>)}
                </Select>
              </div>
              <div className="space-y-1.5">
                <Label htmlFor="n">Pacientes</Label>
                <Input id="n" type="number" min={1} max={300} value={n} onChange={(e) => setN(e.target.value)} />
              </div>
              <div className="space-y-1.5">
                <Label htmlFor="dur">Duração (min)</Label>
                <Input id="dur" type="number" min={30} max={2880} value={duration} onChange={(e) => setDuration(e.target.value)} />
              </div>
              <div className="space-y-1.5">
                <Label htmlFor="seed">Seed (reprodutibilidade)</Label>
                <Input id="seed" type="number" min={0} value={seed} onChange={(e) => setSeed(e.target.value)} />
              </div>
              {Object.keys(capacity).map((k) => (
                <div key={k} className="space-y-1.5">
                  <Label htmlFor={`cap-${k}`}>{k} (unidades)</Label>
                  <Input id={`cap-${k}`} type="number" min={0} max={50} value={capacity[k]} onChange={(e) => setCapacity((c) => ({ ...c, [k]: e.target.value }))} />
                </div>
              ))}
            </CardContent>
          </Card>
        </div>

        <TabsContent value="run" className="space-y-6">
          <Card>
            <CardContent className="flex flex-wrap items-end gap-3 pt-5">
              <div className="min-w-[260px] space-y-1.5">
                <Label htmlFor="preset">Pesos a usar</Label>
                <Select id="preset" value={preset} onChange={(e) => setPreset(e.target.value)}>
                  {Object.entries(WEIGHT_PRESETS).map(([k, v]) => <option key={k} value={k}>{v.label}</option>)}
                </Select>
              </div>
              <Button disabled={action.busy} onClick={run}><Play className="h-4 w-4" /> {action.busy ? "A simular…" : "Executar simulação"}</Button>
            </CardContent>
          </Card>
          {session ? <SessionView session={session} /> : <Empty title="Ainda sem resultados">Escolhe um cenário e executa a simulação.</Empty>}
        </TabsContent>

        <TabsContent value="compare" className="space-y-6">
          <Card>
            <CardHeader>
              <CardTitle>Mesmo cenário, três configurações de pesos</CardTitle>
              <CardDescription>
                Usa a mesma seed para todas: as diferenças vêm só dos pesos. Equilibrado 40/20/30/10, Gravidade 70/5/20/5, Espera 10/70/15/5.
              </CardDescription>
            </CardHeader>
            <CardContent>
              <Button disabled={action.busy} onClick={runCompare}><FlaskConical className="h-4 w-4" /> {action.busy ? "A comparar…" : "Comparar"}</Button>
            </CardContent>
          </Card>
          {compare && (
            <>
              <Card>
                <CardHeader>
                  <CardTitle>Espera média por gravidade</CardTitle>
                  <CardDescription>Menos espera para a gravidade alta indica que o agente a favorece.</CardDescription>
                </CardHeader>
                <CardContent><CompareChart runs={compare.runs} /></CardContent>
              </Card>
              <Card>
                <CardContent className="pt-5">
                  <Table>
                    <THead>
                      <TR><TH>Configuração</TH><TH>Espera média</TH><TH>Gravidade alta</TH><TH>Gravidade baixa</TH><TH>Máxima</TH><TH>Atendidos</TH></TR>
                    </THead>
                    <TBody>
                      {compare.runs.map((r) => (
                        <TR key={r.session_id}>
                          <TD className="font-medium">{r.name}</TD>
                          <TD>{fmtMinutes(r.metrics.avg_wait_minutes)}</TD>
                          <TD>{fmtMinutes(r.metrics.avg_wait_high_severity)}</TD>
                          <TD>{fmtMinutes(r.metrics.avg_wait_low_severity)}</TD>
                          <TD>{fmtMinutes(r.metrics.max_wait_minutes)}</TD>
                          <TD>{r.metrics.served}/{r.metrics.n_patients}</TD>
                        </TR>
                      ))}
                    </TBody>
                  </Table>
                </CardContent>
              </Card>
            </>
          )}
        </TabsContent>

        <TabsContent value="live" className="space-y-6">
          <Card>
            <CardHeader>
              <CardTitle>Fila ao vivo</CardTitle>
              <CardDescription>Gera pacientes fictícios na fila real (dados aleatórios a partir de perfis, sem IA) e avança o tempo: a espera sobe, os atendimentos em curso terminam e o agente reordena.</CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              {liveMsg && <InfoBanner>{liveMsg} <Link className="underline" href="/queue">Ver fila</Link></InfoBanner>}
              <div className="flex flex-wrap items-end gap-6">
                <div className="flex items-end gap-2">
                  <div className="space-y-1.5">
                    <Label htmlFor="genN">Pacientes a gerar</Label>
                    <Input id="genN" className="w-28" type="number" min={1} max={100} value={genN} onChange={(e) => setGenN(e.target.value)} />
                  </div>
                  <Button disabled={action.busy} onClick={generate}>Gerar</Button>
                </div>
                <div className="flex items-end gap-2">
                  <div className="space-y-1.5">
                    <Label htmlFor="adv">Avançar tempo (min)</Label>
                    <Input id="adv" className="w-28" type="number" min={1} max={1440} value={advance} onChange={(e) => setAdvance(e.target.value)} />
                  </div>
                  <Button variant="outline" disabled={action.busy} onClick={advanceTime}>Avançar</Button>
                </div>
              </div>
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="history">
          <Card>
            <CardContent className="pt-5">
              {!sessions.data ? <LoadingBlock rows={3} /> : sessions.data.length === 0 ? (
                <Empty title="Ainda não há sessões">Executa um cenário para guardar resultados.</Empty>
              ) : (
                <Table>
                  <THead><TR><TH>Sessão</TH><TH>Cenário</TH><TH>Pacientes</TH><TH>Seed</TH><TH>Espera média</TH><TH>Data</TH><TH /></TR></THead>
                  <TBody>
                    {sessions.data.map((s) => (
                      <TR key={s.id}>
                        <TD className="font-medium">{s.session_name}</TD>
                        <TD>{s.scenario}</TD>
                        <TD>{s.n_patients}</TD>
                        <TD>{s.seed}</TD>
                        <TD>{fmtNumber(s.avg_wait_minutes)} min</TD>
                        <TD>{fmtDateTime(s.created_at)}</TD>
                        <TD className="text-right"><Button size="sm" variant="subtle" disabled={action.busy} onClick={() => openSession(s.id)}>Abrir</Button></TD>
                      </TR>
                    ))}
                  </TBody>
                </Table>
              )}
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>
    </>
  );
}
