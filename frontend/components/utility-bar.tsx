import { FACTORS } from "@/lib/constants";
import type { Contributions } from "@/types";
import { fmtNumber } from "@/lib/utils";

/** Barra segmentada: cada fator ocupa a fatia dos pontos de utilidade que contribuiu. A escala total é 100. */
export function UtilityBar({ contributions, className, height = 10 }: { contributions: Contributions; className?: string; height?: number }) {
  const total = FACTORS.reduce((s, f) => s + (contributions[f.key] ?? 0), 0);
  return (
    <div
      className={className}
      role="img"
      aria-label={`Utilidade ${fmtNumber(total)} de 100: ${FACTORS.map((f) => `${f.label} ${fmtNumber(contributions[f.key])}`).join(", ")}`}
    >
      <div className="flex w-full overflow-hidden rounded-sm bg-line/70" style={{ height }}>
        {FACTORS.map((f) => {
          const v = Math.max(contributions[f.key] ?? 0, 0);
          return <div key={f.key} title={`${f.label}: ${fmtNumber(v)} pts`} style={{ width: `${v}%`, backgroundColor: f.color }} />;
        })}
      </div>
    </div>
  );
}

export function FactorLegend() {
  return (
    <ul className="flex flex-wrap gap-x-4 gap-y-1 text-xs text-muted">
      {FACTORS.map((f) => (
        <li key={f.key} className="flex items-center gap-1.5">
          <span className="inline-block h-2.5 w-2.5 rounded-sm" style={{ backgroundColor: f.color }} />
          {f.label}
        </li>
      ))}
    </ul>
  );
}
