import type { Config } from "tailwindcss";

const config: Config = {
  content: ["./src/**/*.{ts,tsx}", "./src/app/**/*.{ts,tsx}"],
  theme: {
    extend: {
      fontFamily: {
        display: ["Space Grotesk", "system-ui", "sans-serif"],
        mono: ["JetBrains Mono", "ui-monospace", "SFMono-Regular", "monospace"],
      },
      colors: {
        ink: "#0b0e14",
        fog: "#0f1a22",
        card: "rgba(255,255,255,0.06)",
        border: "rgba(255,255,255,0.12)",
        accent: "#4de3c2",
        accent2: "#5aa7ff",
        muted: "#a8b3c1",
      },
      boxShadow: {
        glow: "0 10px 30px rgba(0,0,0,0.25)",
      },
      backgroundImage: {
        hero: "radial-gradient(1200px 600px at 10% -10%, rgba(90,167,255,0.25), transparent 60%), radial-gradient(900px 600px at 110% 10%, rgba(77,227,194,0.18), transparent 60%), linear-gradient(180deg, #0b0e14, #0f1a22)",
      },
      keyframes: {
        fadeUp: {
          "0%": { opacity: "0", transform: "translateY(8px)" },
          "100%": { opacity: "1", transform: "translateY(0)" },
        },
      },
      animation: {
        fadeUp: "fadeUp 700ms ease-out both",
      },
    },
  },
  plugins: [],
};

export default config;
