import type { Config } from "tailwindcss";

const config: Config = {
  content: ["./app/**/*.{ts,tsx}", "./components/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        background: "var(--background)",
        foreground: "var(--foreground)",
        card: {
          DEFAULT: "var(--card)",
          foreground: "var(--card-foreground)",
        },
        muted: {
          DEFAULT: "var(--muted)",
          foreground: "var(--muted-foreground)",
        },
        border: "var(--border)",
        primary: {
          DEFAULT: "var(--primary)",
          foreground: "var(--primary-foreground)",
        },
        secondary: "var(--secondary)",
        destructive: "var(--destructive)",
      },
      borderColor: {
        DEFAULT: "var(--border)",
      },
      fontFamily: {
        sans: [
          "var(--font-geist-sans)",
          "Pretendard",
          "Apple SD Gothic Neo",
          "Noto Sans KR",
          "system-ui",
          "-apple-system",
          "sans-serif",
        ],
      },
      boxShadow: {
        "card-hover": "0 0 0 1px rgba(40, 224, 255, 0.4), 0 10px 30px rgba(0, 0, 0, 0.35)",
      },
    },
  },
  plugins: [],
};
export default config;
