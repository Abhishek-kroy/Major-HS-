/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        background: "#0a0c10",
        surface: "#0f1318",
        border: "#1e2530",
        primary: "#00d4ff",
        success: "#00e676",
        danger: "#ff3b3b",
        warning: "#ffab00",
        grid: "#12161d",
      },
      fontFamily: {
        mono: ['JetBrains Mono', 'monospace'],
        sans: ['IBM Plex Sans', 'sans-serif'],
      },
      animation: {
        'pulse-fast': 'pulse 1s cubic-bezier(0.4, 0, 0.6, 1) infinite',
      }
    },
  },
  plugins: [],
}
