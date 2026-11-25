"use client";

import { useRouter } from "next/navigation";
import { useEffect, useMemo, useState } from "react";
import { Plus, Trash2 } from "lucide-react";
import { PageHeader } from "@/components/page-header";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input, Label, Select } from "@/components/ui/input";
import { ErrorBanner } from "@/components/feedback";
import { useAction, useApi } from "@/hooks/useApi";
import { patientsService } from "@/services/patients";
import { agentService } from "@/services/agent";
import { VITAL_FIELDS } from "@/lib/constants";
import type { PatientCreate } from "@/types";

interface SymptomRow { description: string; severity: number }

function suggestCode() {
  return `P-${String(Math.floor(Math.random() * 9000) + 1000)}`;
}
// O código sugerido é gerado só no browser (useEffect): gerar com Math.random() no render
// dava um valor no servidor e outro no cliente, o que causa erro de hidratação e deixa a página sem resposta.

export default function NewPatientPage() {
  const router = useRouter();
  const action = useAction();
  const resources = useApi(() => agentService.resources(), []);

  const [code, setCode] = useState("");
  const [showErrors, setShowErrors] = useState(false);
  useEffect(() => {
    setCode((c) => c || suggestCode());
  }, []);
  const [age, setAge] = useState("");
  const [sex, setSex] = useState<"" | "M" | "F">("");
  const [alreadyWaited, setAlreadyWaited] = useState("0");
  const [serviceMinutes, setServiceMinutes] = useState("30");
  const [vitals, setVitals] = useState<Record<string, string>>({});
  const [symptoms, setSymptoms] = useState<SymptomRow[]>([{ description: "", severity: 5 }]);
  const [needs, setNeeds] = useState<Record<number, number>>({});

  const clientError = useMemo(() => {
    const a = Number(age);
    if (!code.trim()) return "Indica o código do paciente.";
    if (age === "" || Number.isNaN(a) || a < 0 || a > 120) return "A idade tem de estar entre 0 e 120 anos.";
    for (const f of VITAL_FIELDS) {
      const raw = vitals[f.key];
      if (raw === undefined || raw === "") continue;
      const v = Number(raw);
      if (Number.isNaN(v) || v < f.min || v > f.max) return `${f.label}: valor entre ${f.min} e ${f.max} ${f.unit}.`;
    }
    const s = Number(vitals.systolic_pressure), d = Number(vitals.diastolic_pressure);
    if (vitals.systolic_pressure && vitals.diastolic_pressure && s <= d) return "A pressão sistólica tem de ser maior que a diastólica.";
    if (serviceMinutes !== "" && (Number(serviceMinutes) < 1 || Number(serviceMinutes) > 1440 || Number.isNaN(Number(serviceMinutes)))) return "A duração do atendimento tem de estar entre 1 e 1440 minutos (ou fica em branco).";
    if (symptoms.some((x) => x.description.trim() !== "" && x.description.trim().length < 2)) return "Descreve cada sintoma com pelo menos 2 caracteres.";
    return null;
  }, [code, age, vitals, symptoms, serviceMinutes]);

  const submit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (clientError) {
      setShowErrors(true);
      return;
    }
    const vs: Record<string, number> = {};
    VITAL_FIELDS.forEach((f) => {
      const raw = vitals[f.key];
      if (raw !== undefined && raw !== "") vs[f.key] = Number(raw);
    });
    const waited = Math.max(Number(alreadyWaited) || 0, 0);
    const payload: PatientCreate = {
      patient_code: code.trim(),
      age: Number(age),
      sex: sex || null,
      vital_signs: Object.keys(vs).length ? vs : null,
      symptoms: symptoms
        .filter((s) => s.description.trim().length >= 2)
        .map((s) => ({ description: s.description.trim(), simulated_severity: s.severity })),
      required_resources: Object.entries(needs).filter(([, q]) => q > 0).map(([id, q]) => ({ resource_id: Number(id), quantity: q })),
      service_minutes: serviceMinutes === "" ? null : Number(serviceMinutes),
      arrived_at: waited > 0 ? new Date(Date.now() - waited * 60000).toISOString() : null,
    };
    const created = await action.run(() => patientsService.create(payload));
    if (created) router.push(`/queue/${created.id}`);
  };

  return (
    <>
      <PageHeader
        title="Registar paciente"
        description="Introduz dados sintéticos para a simulação. Nunca uses dados pessoais reais."
      />
      <ErrorBanner message={action.error} />
      <form onSubmit={submit} className="space-y-6" noValidate>
        <Card>
          <CardHeader><CardTitle>Identificação</CardTitle></CardHeader>
          <CardContent className="grid gap-4 sm:grid-cols-3 lg:grid-cols-5">
            <div className="space-y-1.5">
              <Label htmlFor="code">Código</Label>
              <Input id="code" value={code} onChange={(e) => setCode(e.target.value)} maxLength={32} />
            </div>
            <div className="space-y-1.5">
              <Label htmlFor="age">Idade (anos)</Label>
              <Input id="age" type="number" min={0} max={120} value={age} onChange={(e) => setAge(e.target.value)} />
            </div>
            <div className="space-y-1.5">
              <Label htmlFor="sex">Sexo</Label>
              <Select id="sex" value={sex} onChange={(e) => setSex(e.target.value as "" | "M" | "F")}>
                <option value="">Não indicado</option>
                <option value="M">Masculino</option>
                <option value="F">Feminino</option>
              </Select>
            </div>
            <div className="space-y-1.5">
              <Label htmlFor="waited">Já espera há (min)</Label>
              <Input id="waited" type="number" min={0} value={alreadyWaited} onChange={(e) => setAlreadyWaited(e.target.value)} />
            </div>
            <div className="space-y-1.5">
              <Label htmlFor="service">Duração do atendimento (min)</Label>
              <Input id="service" type="number" min={1} max={1440} placeholder="manual" value={serviceMinutes} onChange={(e) => setServiceMinutes(e.target.value)} />
              <p className="text-xs text-muted">Termina sozinho e liberta recursos. Em branco: conclui-se à mão.</p>
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>Sinais vitais</CardTitle>
            <CardDescription>Todos opcionais. Os que faltarem não entram no cálculo.</CardDescription>
          </CardHeader>
          <CardContent className="grid gap-4 sm:grid-cols-3">
            {VITAL_FIELDS.map((f) => (
              <div key={f.key} className="space-y-1.5">
                <Label htmlFor={f.key}>{f.label} ({f.unit})</Label>
                <Input
                  id={f.key} type="number" step={f.step} min={f.min} max={f.max}
                  placeholder={`${f.min}–${f.max}`}
                  value={vitals[f.key] ?? ""}
                  onChange={(e) => setVitals((v) => ({ ...v, [f.key]: e.target.value }))}
                />
              </div>
            ))}
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>Sintomas</CardTitle>
            <CardDescription>Severidade simulada de 0 (nenhuma) a 10 (máxima).</CardDescription>
          </CardHeader>
          <CardContent className="space-y-3">
            {symptoms.map((s, i) => (
              <div key={i} className="flex flex-wrap items-center gap-3">
                <Input
                  className="min-w-[220px] flex-1" placeholder="Descrição (ex.: falta de ar)" aria-label={`Sintoma ${i + 1}`}
                  value={s.description}
                  onChange={(e) => setSymptoms((rows) => rows.map((r, j) => (j === i ? { ...r, description: e.target.value } : r)))}
                />
                <input
                  type="range" min={0} max={10} step={0.5} value={s.severity} aria-label={`Severidade do sintoma ${i + 1}`}
                  className="w-40 accent-brand"
                  onChange={(e) => setSymptoms((rows) => rows.map((r, j) => (j === i ? { ...r, severity: Number(e.target.value) } : r)))}
                />
                <span className="w-10 text-sm tabular-nums">{s.severity.toFixed(1)}</span>
                <Button type="button" size="icon" variant="ghost" aria-label="Remover sintoma"
                  disabled={symptoms.length === 1} onClick={() => setSymptoms((rows) => rows.filter((_, j) => j !== i))}>
                  <Trash2 className="h-4 w-4" />
                </Button>
              </div>
            ))}
            <Button type="button" variant="outline" size="sm" onClick={() => setSymptoms((r) => [...r, { description: "", severity: 5 }])}>
              <Plus className="h-4 w-4" /> Adicionar sintoma
            </Button>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>Recursos necessários</CardTitle>
            <CardDescription>Unidades que o paciente precisa para ser atendido.</CardDescription>
          </CardHeader>
          <CardContent className="grid gap-4 sm:grid-cols-3">
            {(resources.data ?? []).map((r) => (
              <div key={r.id} className="space-y-1.5">
                <Label htmlFor={`res-${r.id}`}>{r.resource_name} <span className="font-normal text-muted">({r.quantity_free} livre(s))</span></Label>
                <Input
                  id={`res-${r.id}`} type="number" min={0} max={5} value={needs[r.id] ?? 0}
                  onChange={(e) => setNeeds((n) => ({ ...n, [r.id]: Math.max(Number(e.target.value) || 0, 0) }))}
                />
              </div>
            ))}
          </CardContent>
        </Card>

        {showErrors && clientError && <p className="text-sm text-band-vh" role="alert">{clientError}</p>}
        <div className="flex gap-3">
          <Button type="submit" disabled={action.busy}>{action.busy ? "A registar…" : "Registar e avaliar"}</Button>
          <Button type="button" variant="ghost" onClick={() => router.push("/patients")}>Cancelar</Button>
        </div>
      </form>
    </>
  );
}
