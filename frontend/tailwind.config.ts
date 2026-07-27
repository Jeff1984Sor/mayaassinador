import type { Config } from "tailwindcss";

// Paleta MayaCorp — a mesma dos outros produtos do portfolio.
const config: Config = {
  content: ["./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        navy: "#1E2D6B",
        indigo: "#7C8FFF",
        teal: "#1A8F5E",
        amber: "#F5A623",
        risco: "#C94343",
        dark: "#0F1729",
        cinza: "#F7F8FC",
      },
      fontFamily: {
        sans: ["var(--font-dm-sans)", "system-ui", "sans-serif"],
        mono: ["var(--font-jetbrains)", "monospace"],
      },
      boxShadow: {
        card: "0 1px 3px rgba(15,23,41,.06), 0 1px 2px rgba(15,23,41,.04)",
      },
    },
  },
  plugins: [],
};

export default config;
