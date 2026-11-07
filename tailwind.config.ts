import type { Config } from "tailwindcss";
import typography from "@tailwindcss/typography";

const v = (name: string) => `rgb(var(${name}) / <alpha-value>)`;

export default {
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  darkMode: "class",
  theme: {
    extend: {
      colors: {
        bg: v("--bg"),
        surface: { DEFAULT: v("--surface"), 2: v("--surface-2"), 3: v("--surface-3") },
        line: { DEFAULT: v("--line"), strong: v("--line-strong") },
        ink: { DEFAULT: v("--ink"), 2: v("--ink-2"), 3: v("--ink-3") },
        course: v("--course"),
        ok: v("--ok"),
        warn: v("--warn"),
      },
      fontFamily: {
        sans: [
          "-apple-system",
          "BlinkMacSystemFont",
          '"Inter"',
          '"PingFang SC"',
          '"Hiragino Sans GB"',
          '"Microsoft YaHei"',
          '"Noto Sans SC"',
          "sans-serif",
        ],
        serif: [
          '"Source Han Serif SC"',
          '"Noto Serif SC"',
          '"Songti SC"',
          '"STSong"',
          "Georgia",
          "serif",
        ],
        mono: ['"JetBrains Mono"', '"SF Mono"', "ui-monospace", "Menlo", "Monaco", "Consolas", "monospace"],
      },
      maxWidth: {
        prose: "46rem",
      },
    },
  },
  plugins: [typography],
} satisfies Config;
