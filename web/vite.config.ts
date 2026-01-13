import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

export default defineConfig(({ mode }) => ({
  plugins: [react()],
  server: {
    port: 5178
  },
  resolve: {
    alias: {
      scheduler: mode === 'production' 
        ? "scheduler/cjs/scheduler.production.min.js"
        : "scheduler/cjs/scheduler.development.js"
    }
  }
}));
