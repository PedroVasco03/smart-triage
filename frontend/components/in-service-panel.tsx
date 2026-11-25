"use client";

import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Empty, ErrorBanner, LoadingBlock } from "@/components/feedback";
import { useAction, useApi } from "@/hooks/useApi";
import { patientsService } from "@/services/patients";
import { fmtAge, fmtMinutes } from "@/lib/utils";

/** Pacientes em atendimento: terminam sozinhos após a duração prevista, ou aqui, manualmente. */
export function InServicePanel({ version = 0, onChange }: { version?: number; onChange?: () => void }) {
  const list = useApi(() => patientsService.list({ status: "in_service" }), [version], 5000);
  const action = useAction();

  const finish = async (id: number) => {
    await action.run(() => patientsService.setStatus(id, "attended"));
    list.reload();
    onChange?.();
  };

  return (
    <Card>
      <CardHeader>
        <CardTitle>Em atendimento</CardTitle>
        <CardDescription>Concluir um atendimento liberta os recursos que ele ocupava.</CardDescription>
      </CardHeader>
      <CardContent>
        <ErrorBanner message={action.error ?? list.error} />
        {!list.data ? (
          <LoadingBlock rows={2} />
        ) : list.data.length === 0 ? (
          <Empty title="Ninguém em atendimento">Usa “Chamar próximo” para começar um atendimento.</Empty>
        ) : (
          <ul className="divide-y divide-line">
            {list.data.map((p) => (
              <li key={p.id} className="flex flex-wrap items-center justify-between gap-3 py-3">
                <div>
                  <p className="font-medium">{p.patient_code} <span className="font-normal text-muted">· {fmtAge(p.age)}</span></p>
                  <p className="text-xs text-muted">
                    {p.required_resources.length
                      ? `Ocupa: ${p.required_resources.map((r) => `${r.resource_name} ×${r.quantity}`).join(", ")}`
                      : "Não ocupa recursos"}
                    {" · "}
                    {p.service_remaining_minutes != null
                      ? `termina em ${fmtMinutes(p.service_remaining_minutes)}`
                      : "sem duração prevista: conclui manualmente"}
                  </p>
                </div>
                <Button size="sm" variant="subtle" disabled={action.busy} onClick={() => finish(p.id)}>Concluir atendimento</Button>
              </li>
            ))}
          </ul>
        )}
      </CardContent>
    </Card>
  );
}
