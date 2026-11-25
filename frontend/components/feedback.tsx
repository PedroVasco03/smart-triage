import * as React from "react";
import { AlertTriangle, Loader2 } from "lucide-react";
import { Skeleton } from "@/components/ui/skeleton";

export function ErrorBanner({ message }: { message: string | null }) {
  if (!message) return null;
  return (
    <div role="alert" className="mb-4 flex items-start gap-2 rounded-md border border-band-vh/40 bg-band-vh/5 px-3 py-2 text-sm text-band-vh">
      <AlertTriangle className="mt-0.5 h-4 w-4 shrink-0" aria-hidden />
      <span>{message}</span>
    </div>
  );
}

export function InfoBanner({ children }: { children: React.ReactNode }) {
  return <div className="mb-4 rounded-md border border-factor-r/40 bg-factor-r/5 px-3 py-2 text-sm text-[#7a560f]">{children}</div>;
}

export function Spinner() {
  return <Loader2 className="h-4 w-4 animate-spin" aria-label="A carregar" />;
}

export function LoadingBlock({ rows = 4 }: { rows?: number }) {
  return (
    <div className="space-y-2">
      {Array.from({ length: rows }).map((_, i) => (
        <Skeleton key={i} className="h-10 w-full" />
      ))}
    </div>
  );
}

export function Empty({ title, children }: { title: string; children?: React.ReactNode }) {
  return (
    <div className="rounded-lg border border-dashed border-line px-6 py-10 text-center">
      <p className="font-medium">{title}</p>
      {children && <div className="mt-2 text-sm text-muted">{children}</div>}
    </div>
  );
}
