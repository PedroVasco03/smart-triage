import type { Config } from "tailwindcss";

const config: Config = {
  content: ["./app/**/*.{ts,tsx}", "./components/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        ink: "#12202B",
        paper: "#F2F4F3",
        line: "#D5DCDA",
        muted: "#5C6B73",
        brand: { DEFAULT: "#0F766E", dark: "#0B5A54", soft: "#DDEFEC" },
        factor: { g: "#B4412F", e: "#3B6FB6", r: "#C28A1B", a: "#5B7F6A" },
        band: { vh: "#A32A2A", h: "#D2691E", m: "#C28A1B", l: "#6B7F8C" },
      },
      fontFamily: {
        sans: ["ui-sans-serif", "system-ui", "-apple-system", "Segoe UI", "Roboto", "Helvetica Neue", "Arial", "sans-serif"],
      },
      borderRadius: { lg: "10px", md: "7px", sm: "4px" },
    },
  },
  plugins: [],
};
export default config;
