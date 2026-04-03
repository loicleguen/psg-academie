import react from "@vitejs/plugin-react";
import { defineConfig } from "vite";

/**
 * Vite configuration.
 *
 * We proxy API calls to the reverse-proxy (nginx) so the frontend can call:
 *   - /api/physical/*
 *   - /api/tactical/*
 *   - /parse-veo-clipboard
 *
 * This avoids hardcoding backend URLs and prevents 404 on the Vite dev server.
 */
export default defineConfig({
  plugins: [react()],
  server: {
    allowedHosts: true,
    proxy: {
      "/api/physical": {
        target: "http://nginx",
        changeOrigin: true,
      },
      "/api/tactical": {
        target: "http://nginx",
        changeOrigin: true,
      },

      // ✅ Smart Paste endpoint (FastAPI route at root)
      "/parse-veo-clipboard": {
        target: "http://nginx",
        changeOrigin: true,
      },
    },
  },
});
