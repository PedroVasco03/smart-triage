import { api, qs } from "@/lib/api";
import type { Dashboard, EvolutionPoint } from "@/types";

export const statisticsService = {
  dashboard: () => api<Dashboard>("/statistics/dashboard"),
  evolution: (p: { patient_id?: number; limit?: number } = {}) =>
    api<{ patient_id: number | null; points: EvolutionPoint[] }>(`/statistics/utility-evolution${qs(p)}`),
};
