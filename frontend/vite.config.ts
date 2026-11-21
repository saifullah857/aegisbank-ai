import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

// In development, /api is proxied to the FastAPI backend, so the browser never needs a backend URL or any secret.
export default defineConfig({
  plugins: [react()],
  server: { port: 5173, proxy: { "/api": { target: process.env.VITE_PROXY_TARGET || "http://localhost:8000", changeOrigin: true } } },
});
