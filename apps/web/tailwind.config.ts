import type { Config } from "tailwindcss";

const config: Config = {
  content: [
    "./pages/**/*.{js,ts,jsx,tsx,mdx}",
    "./components/**/*.{js,ts,jsx,tsx,mdx}",
    "./app/**/*.{js,ts,jsx,tsx,mdx}",
  ],
  theme: {
    extend: {
      colors: {
        brand: {
          50: "#fff7ed",
          100: "#ffedd5",
          200: "#fed7aa",
          300: "#fdba74",
          400: "#fb923c",
          500: "#f97316",
          600: "#ea580c",
          700: "#c2410c",
          800: "#9a3412",
          900: "#7c2d12",
          DEFAULT: "#ea580c",
        },
        emergency: {
          50: "#fef2f2",
          500: "#ef4444",
          600: "#dc2626",
          700: "#b91c1c",
          DEFAULT: "#dc2626",
        },
        surface: {
          DEFAULT: "#0f172a",
          card: "#1e293b",
          elevated: "#334155",
          border: "#334155",
          subtle: "#1e293b80",
        },
      },
      minHeight: {
        touch: "48px",
      },
      minWidth: {
        touch: "48px",
      },
      fontSize: {
        // Enforce body text >= 16px for mobile readability per AGENTS.md
        base: ["1rem", { lineHeight: "1.5rem" }],
      },
    },
  },
  plugins: [],
};

export default config;
