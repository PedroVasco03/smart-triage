"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { Activity, ListOrdered, FlaskConical, LayoutDashboard, SlidersHorizontal, UserPlus, Users } from "lucide-react";
import { cn } from "@/lib/utils";

const NAV = [
  { href: "/", label: "Painel", icon: LayoutDashboard },
  { href: "/queue", label: "Fila de prioridades", icon: ListOrdered },
  { href: "/patients", label: "Pacientes", icon: Users },
  { href: "/patients/new", label: "Registar paciente", icon: UserPlus },
  { href: "/agent", label: "Agente", icon: SlidersHorizontal },
  { href: "/simulation", label: "Simulação", icon: FlaskConical },
];

export function AppShell({ children }: { children: React.ReactNode }) {
  const path = usePathname();
  const active = (href: string) => (href === "/" ? path === "/" : path === href || (path.startsWith(href + "/") && !NAV.some((n) => n.href !== href && n.href.startsWith(href + "/") && path.startsWith(n.href))));

  return (
    <div className="min-h-screen lg:grid lg:grid-cols-[248px_1fr]">
      <aside className="border-b border-line bg-ink text-white lg:sticky lg:top-0 lg:h-screen lg:border-b-0">
        <div className="flex items-center gap-2 px-5 py-4">
          <Activity className="h-5 w-5 text-[#7fd1c7]" aria-hidden />
          <span className="text-[15px] font-semibold">Triagem inteligente</span>
        </div>
        <nav aria-label="Principal" className="flex gap-1 overflow-x-auto px-3 pb-3 lg:flex-col lg:overflow-visible">
          {NAV.map(({ href, label, icon: Icon }) => (
            <Link
              key={href}
              href={href}
              aria-current={active(href) ? "page" : undefined}
              className={cn(
                "flex shrink-0 items-center gap-2.5 rounded-md px-3 py-2 text-sm transition-colors",
                active(href) ? "bg-white/12 font-medium text-white" : "text-white/70 hover:bg-white/8 hover:text-white",
              )}
            >
              <Icon className="h-4 w-4" aria-hidden />
              {label}
            </Link>
          ))}
        </nav>
      </aside>
      <main className="min-w-0 px-4 py-6 sm:px-8 lg:py-8">
        <div className="mx-auto max-w-6xl">{children}</div>
      </main>
    </div>
  );
}
