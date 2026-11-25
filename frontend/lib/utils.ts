import { clsx, type ClassValue } from "clsx";
import { twMerge } from "tailwind-merge";

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}

export function fmtNumber(n: number | null | undefined, digits = 1): string {
  if (n === null || n === undefined || Number.isNaN(n)) return "–";
  return n.toLocaleString("pt-PT", { minimumFractionDigits: digits, maximumFractionDigits: digits });
}

export function fmtMinutes(m: number | null | undefined): string {
  if (m === null || m === undefined) return "–";
  const total = Math.round(m);
  if (total < 60) return `${total} min`;
  const h = Math.floor(total / 60);
  const r = total % 60;
  return `${h} h ${String(r).padStart(2, "0")} min`;
}

export function fmtDateTime(iso: string | null | undefined): string {
  if (!iso) return "–";
  // o backend envia UTC sem sufixo: tratamos como UTC
  const d = new Date(iso.endsWith("Z") || iso.includes("+") ? iso : `${iso}Z`);
  return d.toLocaleString("pt-PT", { day: "2-digit", month: "2-digit", hour: "2-digit", minute: "2-digit" });
}

export function fmtTime(iso: string | null | undefined): string {
  if (!iso) return "–";
  const d = new Date(iso.endsWith("Z") || iso.includes("+") ? iso : `${iso}Z`);
  return d.toLocaleTimeString("pt-PT", { hour: "2-digit", minute: "2-digit", second: "2-digit" });
}

export function fmtAge(n: number): string {
  return `${n} ${n === 1 ? "ano" : "anos"}`;
}
