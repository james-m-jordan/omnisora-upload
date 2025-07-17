/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        background: "#000000",
        foreground: "#ffffff",
        primary: {
          DEFAULT: "#3b82f6",
          foreground: "#ffffff",
        },
        secondary: {
          DEFAULT: "#111111",
          foreground: "#ffffff",
        },
        accent: {
          DEFAULT: "#1e293b",
          foreground: "#ffffff",
        },
        muted: {
          DEFAULT: "#333333",
          foreground: "#888888",
        },
        border: {
          DEFAULT: "#333333",
        },
        sidebar: {
          DEFAULT: "#111111",
          border: "#333333",
          foreground: "#ffffff",
          accent: "#1e293b",
          "accent-foreground": "#ffffff",
          foreground: "#ffffff",
        },
      },
      fontFamily: {
        sans: ["Inter", "sans-serif"],
      },
    },
  },
  plugins: [],
}
