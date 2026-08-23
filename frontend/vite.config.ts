import { fileURLToPath, URL } from "node:url";
import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import tailwindcss from "@tailwindcss/vite";
import { VitePWA } from "vite-plugin-pwa";

// PWA de Triverde. El proxy /api evita CORS en desarrollo: las Vistas hablan
// con el backend Django (docker/local en :8000) a traves del mismo origen.
export default defineConfig({
  plugins: [
    react(),
    tailwindcss(),
    VitePWA({
      registerType: "autoUpdate",
      manifest: {
        name: "Triverde - Gestion operativa",
        short_name: "Triverde",
        description:
          "Recepcion de camiones, inventario y trazabilidad para Triverde.",
        theme_color: "#166534",
        background_color: "#f8fafc",
        display: "standalone",
        start_url: "/",
        icons: [],
      },
    }),
  ],
  resolve: {
    alias: {
      "@": fileURLToPath(new URL("./src", import.meta.url)),
    },
  },
  server: {
    port: 5173,
    proxy: {
      "/api": {
        target: "http://localhost:8000",
        changeOrigin: true,
      },
    },
  },
});
