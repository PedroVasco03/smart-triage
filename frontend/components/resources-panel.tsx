"use client";

import { useState } from "react";
import { Minus, Plus } from "lucide-react";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input, Label } from "@/components/ui/input";
import { ErrorBanner, LoadingBlock } from "@/components/feedback";
import { useAction, useApi } from "@/hooks/useApi";
import { agentService } from "@/services/agent";

/** Capacidade e ocupação dos recursos do serviço. Alterar reavalia a fila. */
export function ResourcesPanel({ version = 0, onChange }: { version?: number; onChange?: () => void }) {
  const resources = useApi(() => agentService.resources(), [version], 5000);
  const action = useAction();
  const [name, setName] = useState("");
  const [qty, setQty] = useState("1");

  const refresh = () => {
    resources.reload();
    onChange?.();
  };
  const setQuantity = async (id: number, quantity: number) => {
    await action.run(() => agentService.setResource(id, Math.max(quantity, 0)));
    refresh();
  };
  const add = async (e: React.FormEvent) => {
    e.preventDefault();
    const q = Number(qty);
    if (name.trim().length < 2 || Number.isNaN(q) || q < 0) return;
    const created = await action.run(() => agentService.createResource(name.trim(), q));
    if (created) {
      setName("");
      setQty("1");
      refresh();
    }
  };

  return (
    <Card>
      <CardHeader>
        <CardTitle>Recursos do serviço</CardTitle>
        <CardDescription>
          Unidades existentes e em uso. Os atendimentos em curso ocupam recursos até terminarem; aumentar a capacidade
          liberta de imediato quem estava bloqueado.
        </CardDescription>
      </CardHeader>
      <CardContent className="space-y-4">
        <ErrorBanner message={action.error ?? resources.error} />
        {!resources.data ? (
          <LoadingBlock rows={3} />
        ) : (
          <ul className="divide-y divide-line">
            {resources.data.map((r) => {
              const pct = r.quantity_available > 0 ? Math.min((r.quantity_in_use / r.quantity_available) * 100, 100) : 0;
              return (
                <li key={r.id} className="flex items-center justify-between gap-4 py-3">
                  <div className="min-w-0 flex-1">
                    <p className="font-medium">{r.resource_name}</p>
                    <div className="mt-1.5 h-1.5 w-full max-w-[220px] overflow-hidden rounded-sm bg-line/70" aria-hidden>
                      <div className="h-full bg-factor-a" style={{ width: `${pct}%` }} />
                    </div>
                    <p className="mt-1 text-xs text-muted">
                      {r.quantity_in_use} em uso · <span className={r.quantity_free === 0 ? "font-medium text-band-vh" : ""}>{r.quantity_free} livre(s)</span> · total {r.quantity_available}
                    </p>
                  </div>
                  <div className="flex items-center gap-2">
                    <Button size="icon" variant="outline" aria-label={`Menos ${r.resource_name}`}
                      disabled={action.busy || r.quantity_available <= r.quantity_in_use}
                      title={r.quantity_available <= r.quantity_in_use ? "Não dá para ficar abaixo das unidades em uso" : undefined}
                      onClick={() => setQuantity(r.id, r.quantity_available - 1)}>
                      <Minus className="h-4 w-4" />
                    </Button>
                    <span className="w-7 text-center font-semibold" aria-label={`Total de ${r.resource_name}`}>{r.quantity_available}</span>
                    <Button size="icon" variant="outline" aria-label={`Mais ${r.resource_name}`} disabled={action.busy}
                      onClick={() => setQuantity(r.id, r.quantity_available + 1)}>
                      <Plus className="h-4 w-4" />
                    </Button>
                  </div>
                </li>
              );
            })}
          </ul>
        )}
        <form onSubmit={add} className="flex flex-wrap items-end gap-3 border-t border-line pt-4">
          <div className="min-w-[160px] flex-1 space-y-1.5">
            <Label htmlFor="new-resource">Novo tipo de recurso</Label>
            <Input id="new-resource" placeholder="Ex.: Ventilador" value={name} maxLength={80} onChange={(e) => setName(e.target.value)} />
          </div>
          <div className="w-24 space-y-1.5">
            <Label htmlFor="new-resource-qty">Unidades</Label>
            <Input id="new-resource-qty" type="number" min={0} max={1000} value={qty} onChange={(e) => setQty(e.target.value)} />
          </div>
          <Button type="submit" variant="outline" disabled={action.busy || name.trim().length < 2}>Adicionar recurso</Button>
        </form>
      </CardContent>
    </Card>
  );
}
