import { api, qs } from "@/lib/api";
import type { Patient, PatientCreate, Status } from "@/types";

export const patientsService = {
  list: (p: { status?: Status | ""; search?: string; limit?: number } = {}) =>
    api<Patient[]>(`/patients${qs({ status: p.status, search: p.search, limit: p.limit ?? 200 })}`),
  get: (id: number) => api<Patient>(`/patients/${id}`),
  create: (data: PatientCreate) => api<Patient>("/patients", { method: "POST", json: data }),
  setStatus: (id: number, status: Status) => api<Patient>(`/patients/${id}`, { method: "PUT", json: { status } }),
  remove: (id: number) => api<void>(`/patients/${id}`, { method: "DELETE" }),
};
