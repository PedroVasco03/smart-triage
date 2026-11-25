import type { ApiErrorBody } from "@/types";

// Por defeito o browser usa /backend (proxy do Next -> FastAPI), sem CORS.
export const API_URL = process.env.NEXT_PUBLIC_API_URL || "/backend";

export class ApiError extends Error {
  status: number;
  code: string;
  details?: unknown;
  constructor(status: number, code: string, message: string, details?: unknown) {
    super(message);
    this.status = status;
    this.code = code;
    this.details = details;
  }
}

function describeDetails(details: unknown): string {
  if (!Array.isArray(details)) return "";
  return details
    .map((d) => (d && typeof d === "object" && "field" in d ? `${(d as any).field}: ${(d as any).message}` : ""))
    .filter(Boolean)
    .join("; ");
}

export async function api<T>(path: string, init?: RequestInit & { json?: unknown }): Promise<T> {
  const { json, ...rest } = init ?? {};
  let res: Response;
  try {
    res = await fetch(`${API_URL}${path}`, {
      ...rest,
      headers: { ...(json !== undefined ? { "Content-Type": "application/json" } : {}), ...(rest.headers ?? {}) },
      body: json !== undefined ? JSON.stringify(json) : rest.body,
      cache: "no-store",
    });
  } catch {
    throw new ApiError(0, "network", "Sem ligação ao servidor. Confirma que o frontend e o backend (porta 8000) estão a correr.");
  }
  if (res.status === 204) return undefined as T;
  const text = await res.text();
  let body: unknown = null;
  try {
    body = text ? JSON.parse(text) : null;
  } catch {
    // resposta que não é JSON (ex.: o proxy do Next não conseguiu chegar ao backend)
    throw new ApiError(
      res.status, "bad_response",
      `Não consegui falar com o backend (HTTP ${res.status}). Ele está a correr em http://127.0.0.1:8000 (uvicorn main:app --port 8000)?`,
    );
  }
  if (!res.ok) {
    const err = (body as ApiErrorBody | null)?.error;
    const extra = describeDetails(err?.details);
    throw new ApiError(res.status, err?.code ?? "error", `${err?.message ?? "Erro inesperado"}${extra ? ` (${extra})` : ""}`, err?.details);
  }
  return body as T;
}

export function qs(params: Record<string, string | number | undefined | null>): string {
  const p = new URLSearchParams();
  Object.entries(params).forEach(([k, v]) => {
    if (v !== undefined && v !== null && v !== "") p.set(k, String(v));
  });
  const s = p.toString();
  return s ? `?${s}` : "";
}
