import type { Config } from "tailwindcss";

const config: Config = {
  content: [
    "./src/pages/**/*.{js,ts,jsx,tsx,mdx}",
    "./src/components/**/*.{js,ts,jsx,tsx,mdx}",
    "./src/app/**/*.{js,ts,jsx,tsx,mdx}",
  ],
  theme: {
    extend: {
      colors: {
        primary: {
          DEFAULT: "#1e293b", // slate-800 — headers/nav
        },
        accent: {
          DEFAULT: "#10b981", // emerald-500 — CTAs, positive sentiment
        },
        danger: {
          DEFAULT: "#f43f5e", // rose-500 — negative sentiment
        },
        background: {
          DEFAULT: "#f8fafc", // slate-50
        },
      },
    },
  },
  plugins: [],
};

export default config;
