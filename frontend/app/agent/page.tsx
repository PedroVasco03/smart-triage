"use client";

import { useEffect, useMemo, useState } from "react";
import { PageHeader } from "@/components/page-header";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Input, Label } from "@/components/ui/input";
import { Table, TBody, TD, TH, THead, TR } from "@/components/ui/table";
import { ErrorBanner, InfoBanner, LoadingBlock } from "@/components/feedback";
import { ResourcesPanel } from "@/components/resources-panel";
import { useAction, useApi } from "@/hooks/useApi";
import { agentService } from "@/services/agent";
import { FACTORS, VITAL_FIELDS } from "@/lib/constants";
import { fmtDateTime, fmtNumber } from "@/lib/utils";
import type { Weights } from "@/types";

const PRESETS: { name: string; w: Weights }[] = [
  { name: "Equilibrado (40/20/30/10)", w: { w1: 40, w2: 20, w3: 30, w4: 10 } },
  { name: "Gravidade primeiro", w: { w1: 70, w2: 5, w3: 20, w4: 5 } },
  { name: "Espera primeiro", w: { w1: 10, w2: 70, w3: 15, w4: 5 } },
];

type RangeEdit = Record<string, { min: string; max: string; tol_low: string; tol_high: string }>;

export default function AgentPage() {
  const config = useApi(() => agentService.config(), []);
  const history = useApi(() => agentService.history(), []);
  const status = useApi(() => agentService.status(), [], 8000);
  const action = useAction();

  const [weights, setWeights] = useState<Weights>({ w1: 40, w2: 20, w3: 30, w4: 10 });
  const [tau, setTau] = useState("60");
  const [sevShare, setSevShare] = useState("0.6");
  const [ranges, setRanges] = useState<RangeEdit>({});
  const [note, setNote] = useState("");
  const [saved, setSaved] = useState<string[] | null>(null);
  const [loadedVersion, setLoadedVersion] = useState<number | null>(null);

  useEffect(() => {
    const c = config.data;
    if (!c || loadedVersion === c.version) return;
    setLoadedVersion(c.version);
    setWeights(c.weights);
    setTau(String(c.params.tau_minutes));
    setSevShare(String(c.params.severity_vitals_share));
    const r: RangeEdit = {};
    Object.entries(c.params.vital_ranges).forEach(([k, v]) => {
      r[k] = { min: String(v.min), max: String(v.max), tol_low: String(v.tol_low), tol_high: String(v.tol_high) };
    });
    setRanges(r);
  }, [config.data, loadedVersion]);

  const total = weights.w1 + weights.w2 + weights.w3 + weights.w4;
  const norm = useMemo(
    () => (total > 0 ? { w1: weights.w1 / total, w2: weights.w2 / total, w3: weights.w3 / total, w4: weights.w4 / total } : null),
    [weights, total],
  );
  const warn = norm && norm.w2 >= norm.w1;
  const tauNum = Number(tau);
  const shareNum = Number(sevShare);
  const invalid =
    total <= 0 || Number.isNaN(tauNum) || tauNum < 5 || tauNum > 1440 || Number.isNaN(shareNum) || shareNum < 0 || shareNum > 1;

  const save = async () => {
    const vr: Record<string, Record<string, number>> = {};
    Object.entries(ranges).forEach(([k, v]) => {
      vr[k] = { min: Number(v.min), max: Number(v.max), tol_low: Number(v.tol_low), tol_high: Number(v.tol_high) };
    });
    const res = await action.run(() =>
      agentService.updateConfig({
        weights,
        params: { tau_minutes: tauNum, severity_vitals_share: shareNum, vital_ranges: vr },
        note: note.trim() || undefined,
      }),
    );
    if (res) {
      setSaved(res.warnings);
      setNote("");
      config.reload();
      history.reload();
      status.reload();
    }
  };

  return (
    <>
      <PageHeader
        title="Agente"
        description="Pesos e parâmetros da função de utilidade. Ao guardar, nasce uma nova versão e a fila é recalculada."
      />
      <ErrorBanner message={action.error ?? config.error} />
      {saved && (
        <InfoBanner>
          Configuração guardada e fila recalculada.
          {saved.map((w, i) => <span key={i} className="mt-1 block">Aviso: {w}</span>)}
        </InfoBanner>
      )}

      {!config.data ? (
        <LoadingBlock rows={5} />
      ) : (
        <div className="space-y-6">
          <Card>
            <CardHeader>
              <CardTitle>Pesos dos fatores</CardTitle>
              <CardDescription>
                Qualquer escala serve: os pesos são normalizados pela soma. U(p) = w1·G + w2·E + w3·R + w4·A.
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-5">
              <div className="flex flex-wrap gap-2">
                {PRESETS.map((p) => (
                  <Button key={p.name} variant="outline" size="sm" onClick={() => setWeights(p.w)}>{p.name}</Button>
                ))}
              </div>
              <div className="grid gap-5 sm:grid-cols-2">
                {FACTORS.map((f) => {
                  const k = f.weightKey as keyof Weights;
                  return (
                    <div key={f.key} className="space-y-1.5">
                      <div className="flex items-baseline justify-between">
                        <Label htmlFor={`w-${f.key}`}>
                          <span className="mr-2 inline-block h-2.5 w-2.5 rounded-sm align-middle" style={{ backgroundColor: f.color }} />
                          {f.label}
                        </Label>
                        <span className="text-sm font-semibold">{norm ? fmtNumber(norm[k] * 100, 0) : "–"}%</span>
                      </div>
                      <input
                        id={`w-${f.key}`} type="range" min={0} max={100} step={1} value={weights[k]}
                        className="w-full" style={{ accentColor: f.color }}
                        onChange={(e) => setWeights((w) => ({ ...w, [k]: Number(e.target.value) }))}
                      />
                      <p className="text-xs text-muted">{f.hint}</p>
                    </div>
                  );
                })}
              </div>
              {total <= 0 && <p className="text-sm text-band-vh">A soma dos pesos tem de ser maior que zero.</p>}
              {warn && (
                <p className="text-sm text-[#7a560f]">
                  O peso da espera é igual ou superior ao da gravidade: a espera pode passar à frente da gravidade na fila.
                </p>
              )}
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle>Parâmetros experimentais</CardTitle>
              <CardDescription>Intervalos e constantes usados para normalizar. Não são critérios clínicos validados.</CardDescription>
            </CardHeader>
            <CardContent className="space-y-5">
              <div className="grid gap-4 sm:grid-cols-2">
                <div className="space-y-1.5">
                  <Label htmlFor="tau">Constante de tempo da espera (min)</Label>
                  <Input id="tau" type="number" min={5} max={1440} value={tau} onChange={(e) => setTau(e.target.value)} />
                  <p className="text-xs text-muted">E = 100·(1 − e^(−t/τ)). Com τ = 60, 1 h de espera dá E ≈ 63.</p>
                </div>
                <div className="space-y-1.5">
                  <Label htmlFor="share">Peso dos sinais vitais na gravidade (0–1)</Label>
                  <Input id="share" type="number" min={0} max={1} step={0.05} value={sevShare} onChange={(e) => setSevShare(e.target.value)} />
                  <p className="text-xs text-muted">G = a·V + (1 − a)·S. O resto vem da severidade dos sintomas.</p>
                </div>
              </div>
              <details>
                <summary className="cursor-pointer text-sm font-medium">Intervalos de referência dos sinais vitais</summary>
                <div className="mt-3">
                  <Table>
                    <THead>
                      <TR><TH>Sinal</TH><TH>Mín.</TH><TH>Máx.</TH><TH>Tolerância abaixo</TH><TH>Tolerância acima</TH></TR>
                    </THead>
                    <TBody>
                      {VITAL_FIELDS.map((f) => {
                        const r = ranges[f.key];
                        if (!r) return null;
                        const set = (field: keyof typeof r, v: string) => setRanges((all) => ({ ...all, [f.key]: { ...all[f.key], [field]: v } }));
                        return (
                          <TR key={f.key}>
                            <TD>{f.label} ({f.unit})</TD>
                            {(["min", "max", "tol_low", "tol_high"] as const).map((field) => (
                              <TD key={field}><Input className="h-8 w-24" type="number" step="any" value={r[field]} aria-label={`${f.label} ${field}`} onChange={(e) => set(field, e.target.value)} /></TD>
                            ))}
                          </TR>
                        );
                      })}
                    </TBody>
                  </Table>
                  <p className="mt-2 text-xs text-muted">O desvio sobe de 0 a 100 à medida que o valor se afasta do intervalo, até à distância de tolerância.</p>
                </div>
              </details>
              <div className="flex flex-wrap items-end gap-3">
                <div className="min-w-[240px] flex-1 space-y-1.5">
                  <Label htmlFor="note">Nota desta versão (opcional)</Label>
                  <Input id="note" value={note} maxLength={255} onChange={(e) => setNote(e.target.value)} placeholder="Ex.: dar mais peso à espera" />
                </div>
                <Button disabled={action.busy || invalid} onClick={save}>{action.busy ? "A guardar…" : "Guardar e recalcular"}</Button>
              </div>
            </CardContent>
          </Card>

          <div className="grid gap-6 lg:grid-cols-2">
            <ResourcesPanel onChange={() => status.reload()} />

            <Card>
              <CardHeader>
                <CardTitle>Estado e ciclo do agente</CardTitle>
                <CardDescription>{status.data?.agent_type ?? "Agente baseado em utilidade"}</CardDescription>
              </CardHeader>
              <CardContent className="space-y-3 text-sm">
                <ol className="flex flex-wrap gap-2">
                  {(status.data?.decision_cycle ?? []).map((s) => <li key={s}><Badge>{s}</Badge></li>)}
                </ol>
                {status.data && (
                  <dl className="grid grid-cols-2 gap-y-1.5">
                    <dt className="text-muted">Configuração ativa</dt><dd>v{status.data.config_version}</dd>
                    <dt className="text-muted">Na fila</dt><dd>{status.data.queue_size}</dd>
                    <dt className="text-muted">Em atendimento</dt><dd>{status.data.in_service}</dd>
                    <dt className="text-muted">Avaliações guardadas</dt><dd>{status.data.total_evaluations}</dd>
                    <dt className="text-muted">Última avaliação</dt><dd>{fmtDateTime(status.data.last_evaluation_at)}</dd>
                  </dl>
                )}
              </CardContent>
            </Card>
          </div>

          <Card>
            <CardHeader>
              <CardTitle>Histórico de configurações</CardTitle>
              <CardDescription>Cada alteração de pesos fica guardada como uma versão.</CardDescription>
            </CardHeader>
            <CardContent>
              {!history.data ? <LoadingBlock rows={2} /> : (
                <Table>
                  <THead><TR><TH>Versão</TH><TH>Pesos (G / E / R / A)</TH><TH>Nota</TH><TH>Criada</TH><TH /></TR></THead>
                  <TBody>
                    {history.data.map((h) => (
                      <TR key={h.id}>
                        <TD className="font-medium">v{h.version}</TD>
                        <TD>{["w1", "w2", "w3", "w4"].map((k) => fmtNumber((h.normalized_weights as any)[k] * 100, 0)).join(" / ")}</TD>
                        <TD className="text-muted">{h.note ?? "–"}</TD>
                        <TD>{fmtDateTime(h.created_at)}</TD>
                        <TD>{h.is_active && <Badge color="#0F766E">Ativa</Badge>}</TD>
                      </TR>
                    ))}
                  </TBody>
                </Table>
              )}
            </CardContent>
          </Card>
        </div>
      )}
    </>
  );
}
