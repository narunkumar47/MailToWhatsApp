import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

export default defineConfig({
  plugins: [react()],

  server: {
    host: "0.0.0.0",

    allowedHosts: [
      "stir-distance-cognition.ngrok-free.dev",
    ],

    proxy: {
      "/users": {
        target: "http://127.0.0.1:8000",
        changeOrigin: true,
      },

      "/emails": {
        target: "http://127.0.0.1:8000",
        changeOrigin: true,
      },

      "/auth": {
        target: "http://127.0.0.1:8000",
        changeOrigin: true,
      },

      "/whatsapp": {
        target: "http://127.0.0.1:8000",
        changeOrigin: true,
      },

      "/health": {
        target: "http://127.0.0.1:8000",
        changeOrigin: true,
      },
    },
  },
});