import { api, qs } from "@/lib/api";
import type { CallNext, HistoryItem, Queue, QueueDetail } from "@/types";

export const queueService = {
  get: () => api<Queue>("/queue"),
  detail: (id: number) => api<QueueDetail>(`/queue/${id}`),
  history: (p: { patient_id?: number; limit?: number } = {}) => api<HistoryItem[]>(`/queue/history${qs(p)}`),
  recalculate: () => api<Queue>("/queue/recalculate", { method: "POST" }),
  callNext: () => api<CallNext>("/queue/call-next", { method: "POST" }),
};
