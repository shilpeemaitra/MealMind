import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import { VitePWA } from "vite-plugin-pwa";

// Vite dev server on 5173. The app talks to the Spring Boot API via
// VITE_API_BASE_URL (see .env.example), defaulting to localhost:8080.
//
// VitePWA makes the app installable on a phone home screen (full-screen, app
// icon, offline shell). The service worker is auto-generated and auto-updates.
export default defineConfig({
  plugins: [
    react(),
    VitePWA({
      registerType: "autoUpdate",
      includeAssets: ["favicon.svg", "apple-touch-icon.png"],
      manifest: {
        name: "MealMind — zero-waste meal planner",
        short_name: "MealMind",
        description:
          "AI meal planner that uses up what's in your pantry to cut food waste.",
        theme_color: "#c66b3d",
        background_color: "#f7f5f0",
        display: "standalone",
        orientation: "portrait",
        start_url: "/",
        icons: [
          {
            src: "pwa-192.png",
            sizes: "192x192",
            type: "image/png",
          },
          {
            src: "pwa-512.png",
            sizes: "512x512",
            type: "image/png",
          },
          {
            src: "pwa-512.png",
            sizes: "512x512",
            type: "image/png",
            purpose: "maskable",
          },
        ],
      },
      workbox: {
        // Cache the app shell so it opens instantly / offline. API calls (POST)
        // are never cached — they always hit the network.
        globPatterns: ["**/*.{js,css,html,svg,png,ico}"],
        navigateFallback: "/index.html",
      },
    }),
  ],
  server: {
    port: 5173,
  },
});
