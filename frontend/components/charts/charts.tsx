"use client";

import {
  Bar, BarChart, CartesianGrid, Cell, Legend, Line, LineChart, ResponsiveContainer, Tooltip, XAxis, YAxis,
} from "recharts";
import { BAND_COLORS, FACTORS } from "@/lib/constants";
import { fmtTime } from "@/lib/utils";
import type { CompareRun, EvolutionPoint, TimelinePoint } from "@/types";

const axis = { fontSize: 12, fill: "#5C6B73" };
const grid = "#E4E9E8";

function Wrap({ height = 260, children }: { height?: number; children: React.ReactElement }) {
  return (
    <div style={{ width: "100%", height }}>
      <ResponsiveContainer width="100%" height="100%">
        {children}
      </ResponsiveContainer>
    </div>
  );
}

export function DistributionChart({ data }: { data: { band: string; count: number }[] }) {
  return (
    <Wrap height={220}>
      <BarChart data={data} margin={{ top: 8, right: 8, left: -16, bottom: 0 }}>
        <CartesianGrid stroke={grid} vertical={false} />
        <XAxis dataKey="band" tick={axis} tickLine={false} axisLine={false} />
        <YAxis allowDecimals={false} tick={axis} tickLine={false} axisLine={false} />
        <Tooltip cursor={{ fill: "#0F766E10" }} formatter={(v) => [v, "Pacientes"]} />
        <Bar dataKey="count" radius={[4, 4, 0, 0]}>
          {data.map((d) => (
            <Cell key={d.band} fill={BAND_COLORS[d.band] ?? "#6B7F8C"} />
          ))}
        </Bar>
      </BarChart>
    </Wrap>
  );
}

export function QueueEvolutionChart({ points }: { points: EvolutionPoint[] }) {
  const data = points.map((p) => ({ ...p, label: fmtTime(p.t) }));
  return (
    <Wrap>
      <LineChart data={data} margin={{ top: 8, right: 12, left: -16, bottom: 0 }}>
        <CartesianGrid stroke={grid} vertical={false} />
        <XAxis dataKey="label" tick={axis} tickLine={false} axisLine={false} minTickGap={32} />
        <YAxis domain={[0, 100]} tick={axis} tickLine={false} axisLine={false} />
        <Tooltip />
        <Legend wrapperStyle={{ fontSize: 12 }} />
        <Line type="monotone" dataKey="avg_utility" name="Utilidade média" stroke="#0F766E" strokeWidth={2} dot={false} />
        <Line type="monotone" dataKey="max_utility" name="Utilidade máxima" stroke="#A32A2A" strokeWidth={2} dot={false} />
      </LineChart>
    </Wrap>
  );
}

export function PatientEvolutionChart({ points }: { points: EvolutionPoint[] }) {
  const data = points.map((p) => ({ ...p, label: fmtTime(p.t) }));
  return (
    <Wrap>
      <LineChart data={data} margin={{ top: 8, right: 12, left: -16, bottom: 0 }}>
        <CartesianGrid stroke={grid} vertical={false} />
        <XAxis dataKey="label" tick={axis} tickLine={false} axisLine={false} minTickGap={32} />
        <YAxis domain={[0, 100]} tick={axis} tickLine={false} axisLine={false} />
        <Tooltip />
        <Legend wrapperStyle={{ fontSize: 12 }} />
        <Line type="monotone" dataKey="utility" name="Utilidade" stroke="#12202B" strokeWidth={2.5} dot={false} />
        {FACTORS.map((f) => (
          <Line key={f.key} type="monotone" dataKey={f.key} name={f.label} stroke={f.color} strokeWidth={1.5} dot={false} strokeDasharray="4 3" />
        ))}
      </LineChart>
    </Wrap>
  );
}

export function SimTimelineChart({ points }: { points: TimelinePoint[] }) {
  return (
    <Wrap>
      <LineChart data={points} margin={{ top: 8, right: 12, left: -16, bottom: 0 }}>
        <CartesianGrid stroke={grid} vertical={false} />
        <XAxis dataKey="t" tick={axis} tickLine={false} axisLine={false} tickFormatter={(v) => `${v} min`} minTickGap={40} />
        <YAxis yAxisId="q" allowDecimals={false} tick={axis} tickLine={false} axisLine={false} />
        <YAxis yAxisId="u" orientation="right" domain={[0, 100]} tick={axis} tickLine={false} axisLine={false} />
        <Tooltip labelFormatter={(v) => `t = ${v} min`} />
        <Legend wrapperStyle={{ fontSize: 12 }} />
        <Line yAxisId="q" type="stepAfter" dataKey="queue_length" name="Pacientes na fila" stroke="#3B6FB6" strokeWidth={2} dot={false} />
        <Line yAxisId="u" type="monotone" dataKey="avg_utility" name="Utilidade média (fila)" stroke="#B4412F" strokeWidth={2} dot={false} connectNulls />
      </LineChart>
    </Wrap>
  );
}

export function CompareChart({ runs }: { runs: CompareRun[] }) {
  const data = runs.map((r) => ({
    name: r.name,
    "Gravidade alta": r.metrics.avg_wait_high_severity,
    "Gravidade média": r.metrics.avg_wait_medium_severity,
    "Gravidade baixa": r.metrics.avg_wait_low_severity,
  }));
  return (
    <Wrap height={300}>
      <BarChart data={data} margin={{ top: 8, right: 12, left: -8, bottom: 0 }}>
        <CartesianGrid stroke={grid} vertical={false} />
        <XAxis dataKey="name" tick={axis} tickLine={false} axisLine={false} />
        <YAxis tick={axis} tickLine={false} axisLine={false} unit=" min" />
        <Tooltip formatter={(v) => (typeof v === "number" ? `${v.toFixed(1)} min` : "–")} />
        <Legend wrapperStyle={{ fontSize: 12 }} />
        <Bar dataKey="Gravidade alta" fill="#B4412F" radius={[3, 3, 0, 0]} />
        <Bar dataKey="Gravidade média" fill="#C28A1B" radius={[3, 3, 0, 0]} />
        <Bar dataKey="Gravidade baixa" fill="#6B7F8C" radius={[3, 3, 0, 0]} />
      </BarChart>
    </Wrap>
  );
}
