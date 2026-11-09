import type { Config } from "tailwindcss";

/** Jetons WIGO — cahier des charges §7.1 et §7.3. */
const config: Config = {
  content: ["./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        brique: { DEFAULT: "#A2694F", fonce: "#7A4A36", profond: "#4F2F23" },
        sable: "#E3CDB9",
        creme: "#F6EDE4",
        papier: "#FCF8F4",
        encre: "#1B1A22",
        nuit: "#2F4C7A",
        or: "#E2B33C",
        gris: "#756963",
      },
      fontFamily: {
        display: ["'Playfair Display Variable'", "Georgia", "serif"],
        sans: ["'DM Sans Variable'", "system-ui", "sans-serif"],
      },
      borderRadius: { card: "18px", panel: "26px", pill: "999px" },
      boxShadow: {
        card: "0 1px 2px rgba(27,26,34,0.06), 0 8px 24px -12px rgba(27,26,34,0.25)",
        panel: "0 12px 40px -16px rgba(27,26,34,0.35)",
      },
      aspectRatio: { poster: "4 / 5", story: "9 / 16" },
      backgroundImage: {
        rings: "radial-gradient(circle at 70% 30%, rgba(255,255,255,0.18) 0 18%, transparent 19% 30%, rgba(255,255,255,0.12) 31% 44%, transparent 45% 58%, rgba(255,255,255,0.08) 59% 72%, transparent 73%)",
      },
    },
  },
  plugins: [],
};

export default config;
