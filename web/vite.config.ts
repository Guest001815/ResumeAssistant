import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

export default defineConfig({
  plugins: [react()],
  server: {
    port: 5178
  },
  resolve: {
    alias: {
      scheduler: "scheduler/cjs/scheduler.development.js"
    }
  }
});
