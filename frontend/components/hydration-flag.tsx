"use client";

import { useEffect } from "react";

/** Marca o <html> quando o React arrancou; sem isto o aviso #js-warning (layout) fica visível. */
export function HydrationFlag() {
  useEffect(() => {
    document.documentElement.dataset.hydrated = "1";
  }, []);
  return null;
}
