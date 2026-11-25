import { api } from "@/lib/api";
import type { AgentConfig, AgentParams, AgentStatus, Resource, Weights } from "@/types";

export interface ConfigUpdateBody {
  weights?: Weights;
  params?: Partial<Omit<AgentParams, "vital_ranges" | "priority_bands">> & {
    vital_ranges?: Record<string, Partial<{ min: number; max: number; tol_low: number; tol_high: number }>>;
  };
  note?: string;
}

export const agentService = {
  status: () => api<AgentStatus>("/agent/status"),
  config: () => api<AgentConfig>("/agent/configuration"),
  history: () => api<AgentConfig[]>("/agent/configuration/history"),
  updateConfig: (body: ConfigUpdateBody) => api<AgentConfig>("/agent/configuration", { method: "PUT", json: body }),
  resources: () => api<Resource[]>("/resources"),
  createResource: (resource_name: string, quantity_available: number) =>
    api<Resource>("/resources", { method: "POST", json: { resource_name, quantity_available } }),
  setResource: (id: number, quantity_available: number) =>
    api<Resource>(`/resources/${id}`, { method: "PUT", json: { quantity_available } }),
};
