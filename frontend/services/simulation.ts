import { api } from "@/lib/api";
import type { CompareResponse, Patient, Scenario, SimResult, SimSession, SimSessionItem, Weights } from "@/types";

export interface StartBody {
  scenario: string;
  session_name?: string;
  n_patients: number;
  duration_minutes: number;
  seed: number;
  weights_override?: Weights;
  capacity?: Record<string, number>;
}

export const simulationService = {
  scenarios: () => api<Scenario[]>("/simulation/scenarios"),
  start: (body: StartBody) => api<SimSession>("/simulation/start", { method: "POST", json: body }),
  compare: (body: {
    scenario: string; n_patients: number; duration_minutes: number; seed: number;
    capacity?: Record<string, number>; weight_sets: { name: string; weights: Weights }[];
  }) => api<CompareResponse>("/simulation/compare", { method: "POST", json: body }),
  sessions: () => api<SimSessionItem[]>("/simulation/sessions"),
  session: (id: number) => api<SimSession>(`/simulation/sessions/${id}`),
  results: (id: number) => api<SimResult[]>(`/simulation/sessions/${id}/results`),
  generate: (n: number, seed: number) =>
    api<Patient[]>("/simulation/generate", { method: "POST", json: { n, seed, max_wait_minutes: 90 } }),
  advanceTime: (minutes: number) =>
    api<{ advanced_minutes: number; patients_affected: number; services_completed: string[] }>("/simulation/advance-time", { method: "POST", json: { minutes } }),
};
