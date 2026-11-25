"use client";

import Link from "next/link";
import { useState } from "react";
import { PageHeader } from "@/components/page-header";
import { Card } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input, Select } from "@/components/ui/input";
import { Badge } from "@/components/ui/badge";
import { Table, TBody, TD, TH, THead, TR } from "@/components/ui/table";
import { Empty, ErrorBanner, LoadingBlock } from "@/components/feedback";
import { useAction, useApi } from "@/hooks/useApi";
import { patientsService } from "@/services/patients";
import { STATUS_LABELS } from "@/lib/constants";
import { fmtMinutes } from "@/lib/utils";
import type { Status } from "@/types";

export default function PatientsPage() {
  const [status, setStatus] = useState<Status | "">("");
  const [search, setSearch] = useState("");
  const list = useApi(() => patientsService.list({ status, search }), [status, search], 10000);
  const action = useAction();

  const finish = async (id: number) => {
    await action.run(() => patientsService.setStatus(id, "attended"));
    list.reload();
  };
  const remove = async (id: number, code: string) => {
    if (!window.confirm(`Remover o paciente ${code}? O histórico dele também é apagado.`)) return;
    await action.run(() => patientsService.remove(id));
    list.reload();
  };

  return (
    <>
      <PageHeader
        title="Pacientes"
        description="Pacientes da fila real (fora das sessões de simulação). Todos os dados são sintéticos."
        actions={<Button asChild><Link href="/patients/new">Registar paciente</Link></Button>}
      />
      <ErrorBanner message={list.error ?? action.error} />
      <div className="mb-4 flex flex-wrap gap-3">
        <Input className="max-w-xs" placeholder="Procurar por código" value={search} onChange={(e) => setSearch(e.target.value)} aria-label="Procurar por código" />
        <Select className="w-48" value={status} onChange={(e) => setStatus(e.target.value as Status | "")} aria-label="Filtrar por estado">
          <option value="">Todos os estados</option>
          {Object.entries(STATUS_LABELS).map(([k, v]) => (
            <option key={k} value={k}>{v}</option>
          ))}
        </Select>
      </div>
      <Card>
        {!list.data ? (
          <div className="p-5"><LoadingBlock /></div>
        ) : list.data.length === 0 ? (
          <div className="p-5"><Empty title="Nenhum paciente encontrado">Regista um paciente ou gera pacientes fictícios na página Simulação.</Empty></div>
        ) : (
          <Table>
            <THead>
              <TR>
                <TH>Código</TH><TH>Idade</TH><TH>Sintomas</TH><TH>Estado</TH><TH>Espera</TH><TH>Posição</TH><TH className="text-right">Ações</TH>
              </TR>
            </THead>
            <TBody>
              {list.data.map((p) => (
                <TR key={p.id}>
                  <TD className="font-medium">
                    <Link className="underline-offset-2 hover:underline" href={`/queue/${p.id}`}>{p.patient_code}</Link>
                  </TD>
                  <TD>{p.age}</TD>
                  <TD className="max-w-[260px] truncate text-muted">{p.symptoms.map((s) => s.description).join(", ") || "–"}</TD>
                  <TD>
                    <Badge>{STATUS_LABELS[p.status] ?? p.status}</Badge>
                    {p.status === "in_service" && p.service_remaining_minutes != null && (
                      <span className="ml-2 text-xs text-muted">termina em {fmtMinutes(p.service_remaining_minutes)}</span>
                    )}
                  </TD>
                  <TD>{fmtMinutes(p.waiting_minutes)}</TD>
                  <TD>{p.queue_position ?? "–"}</TD>
                  <TD className="text-right">
                    <div className="flex justify-end gap-2">
                      {p.status === "in_service" && (
                        <Button size="sm" variant="subtle" disabled={action.busy} onClick={() => finish(p.id)}>Concluir atendimento</Button>
                      )}
                      <Button size="sm" variant="ghost" disabled={action.busy} onClick={() => remove(p.id, p.patient_code)}>Remover</Button>
                    </div>
                  </TD>
                </TR>
              ))}
            </TBody>
          </Table>
        )}
      </Card>
    </>
  );
}
