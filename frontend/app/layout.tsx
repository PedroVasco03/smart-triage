import type { Metadata } from "next";
import "./globals.css";
import { AppShell } from "@/components/app-shell";
import { HydrationFlag } from "@/components/hydration-flag";

export const metadata: Metadata = {
  title: "Smart Triage — agente baseado em utilidade",
  description: "Simulação académica de priorização de pacientes com um agente baseado em utilidade.",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="pt-PT" suppressHydrationWarning>
      {/* suppressHydrationWarning: extensões do browser (ex.: Chrome) acrescentam atributos ao <html>/<body> antes do React arrancar */}
      <body suppressHydrationWarning>
        <div id="js-warning" role="alert">
          A interface não arrancou (o JavaScript não carregou), por isso os botões e formulários não respondem. Abre
          o sistema em <strong>http://localhost:3000</strong>, confirma que o <code>npm run dev</code> está ativo e recarrega a página.
        </div>
        <HydrationFlag />
        <AppShell>{children}</AppShell>
      </body>
    </html>
  );
}
