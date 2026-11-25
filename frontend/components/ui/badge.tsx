import * as React from "react";
import { cn } from "@/lib/utils";

export function Badge({
  className, color, ...p
}: React.HTMLAttributes<HTMLSpanElement> & { color?: string }) {
  return (
    <span
      className={cn("inline-flex items-center rounded-sm border px-2 py-0.5 text-xs font-medium", className)}
      style={color ? { color, borderColor: color, backgroundColor: `${color}14` } : undefined}
      {...p}
    />
  );
}
