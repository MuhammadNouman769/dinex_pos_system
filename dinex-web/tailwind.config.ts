import type { Config } from "tailwindcss";

const token = (name: string) => `rgb(var(--${name}) / <alpha-value>)`;

const config: Config = {
  darkMode: "class",
  content: ["./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        bg: token("bg"),
        surface: token("surface"),
        sunken: token("sunken"),
        line: token("line"),
        ink: token("ink"),
        muted: token("muted"),
        brand: { DEFAULT: token("brand"), strong: token("brand-strong"), soft: token("brand-soft") },
        good: { DEFAULT: token("good"), soft: token("good-soft") },
        warn: { DEFAULT: token("warn"), soft: token("warn-soft") },
        bad: { DEFAULT: token("bad"), soft: token("bad-soft") },
        side: { DEFAULT: token("side"), ink: token("side-ink"), hover: token("side-hover") },
        accent: token("accent"),
      },
      fontFamily: {
        sans: ['"Inter Variable"', "Inter", "ui-sans-serif", "system-ui", "-apple-system", "Segoe UI", "Roboto", "sans-serif"],
        display: ['"Plus Jakarta Sans Variable"', '"Inter Variable"', "ui-sans-serif", "system-ui", "sans-serif"],
      },
      boxShadow: {
        card: "0 1px 1px rgb(14 26 22 / 0.03), 0 2px 6px rgb(14 26 22 / 0.04), 0 10px 24px -8px rgb(14 26 22 / 0.06)",
        pop: "0 20px 60px -10px rgb(14 26 22 / 0.35)",
        glow: "0 8px 28px rgb(var(--brand) / 0.28)",
      },
      borderRadius: { lg: "0.6rem", xl: "0.8rem", "2xl": "1.1rem", "3xl": "1.5rem" },
    },
  },
  plugins: [],
};
export default config;
