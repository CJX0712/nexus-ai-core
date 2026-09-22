import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

// NexusAI 控制台构建配置（作者: 晨星）
export default defineConfig({
  plugins: [react()],
  server: {
    host: "0.0.0.0",
    port: 5173,
    proxy: {
      "/health": { target: "http://localhost:8000", changeOrigin: true },
      "/v1": { target: "http://localhost:8000", changeOrigin: true },
      "/docs": { target: "http://localhost:8000", changeOrigin: true },
      "/openapi.json": { target: "http://localhost:8000", changeOrigin: true },
    },
  },
  build: { outDir: "dist", sourcemap: false },
});
