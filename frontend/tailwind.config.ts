import type { Config } from "tailwindcss";

const config: Config = {
  content: ["./src/**/*.{ts,tsx}", "./src/app/**/*.{ts,tsx}"],
  theme: {
    extend: {
      fontFamily: {
        display: ["Outfit", "system-ui", "sans-serif"],
        mono: ["DM Mono", "ui-monospace", "SFMono-Regular", "monospace"],
      },
      colors: {
        ink: "#06080f",
        fog: "#0c1220",
        card: "rgba(255,255,255,0.04)",
        border: "rgba(255,255,255,0.08)",
        accent: "#f59e0b",
        accent2: "#38bdf8",
        signal: "#10b981",
        danger: "#ef4444",
        muted: "#94a3b8",
      },
      boxShadow: {
        glow: "0 0 0 1px rgba(245,158,11,0.06), 0 8px 32px rgba(0,0,0,0.5)",
        "glow-sm": "0 0 0 1px rgba(245,158,11,0.04), 0 4px 16px rgba(0,0,0,0.35)",
        amber: "0 0 20px rgba(245,158,11,0.2)",
      },
      backgroundImage: {
        hero: "radial-gradient(ellipse 110% 55% at 75% -15%, rgba(245,158,11,0.09), transparent 65%), radial-gradient(ellipse 75% 50% at 15% 115%, rgba(56,189,248,0.07), transparent 60%), linear-gradient(175deg, #06080f 0%, #0c1220 55%, #06080f 100%)",
      },
      keyframes: {
        fadeUp: {
          "0%": { opacity: "0", transform: "translateY(10px)" },
          "100%": { opacity: "1", transform: "translateY(0)" },
        },
        fadeIn: {
          "0%": { opacity: "0" },
          "100%": { opacity: "1" },
        },
        slideIn: {
          "0%": { opacity: "0", transform: "translateX(-6px)" },
          "100%": { opacity: "1", transform: "translateX(0)" },
        },
        shimmer: {
          "0%": { backgroundPosition: "-200% 0" },
          "100%": { backgroundPosition: "200% 0" },
        },
      },
      animation: {
        fadeUp: "fadeUp 600ms ease-out both",
        fadeIn: "fadeIn 500ms ease-out both",
        slideIn: "slideIn 400ms ease-out both",
        shimmer: "shimmer 2s linear infinite",
      },
    },
  },
  plugins: [],
};

export default config;
