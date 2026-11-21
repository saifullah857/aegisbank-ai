/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        brand: { 50: "#FFF4EC", 100: "#FFE5D1", 200: "#FFC9A0", 400: "#FF8C42", 500: "#F36F21", 600: "#D95A12", 700: "#B3470C" },
        ink: { 900: "#101B33", 800: "#1B2A4A", 700: "#2E3F63", 500: "#5B6B8C", 400: "#8592AD", 300: "#B5BFD3", 200: "#DCE2EE", 100: "#EDF0F6", 50: "#F6F8FB" },
      },
      fontFamily: { sans: ["Inter", "ui-sans-serif", "system-ui", "-apple-system", "Segoe UI", "Roboto", "sans-serif"] },
      boxShadow: { card: "0 1px 2px rgba(16,27,51,.06), 0 1px 3px rgba(16,27,51,.04)", pop: "0 8px 24px rgba(16,27,51,.14)" },
      keyframes: {
        fadeUp: { from: { opacity: 0, transform: "translateY(6px)" }, to: { opacity: 1, transform: "none" } },
        pulseRing: { "0%": { boxShadow: "0 0 0 0 rgba(243,111,33,.45)" }, "100%": { boxShadow: "0 0 0 10px rgba(243,111,33,0)" } },
      },
      animation: { fadeUp: "fadeUp .25s ease-out both", pulseRing: "pulseRing 1.2s ease-out infinite" },
    },
  },
  plugins: [],
};
