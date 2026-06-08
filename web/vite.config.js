import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

// Vite dev server on 5173. The app talks to the Spring Boot API via
// VITE_API_BASE_URL (see .env.example), defaulting to localhost:8080.
export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
  },
});
