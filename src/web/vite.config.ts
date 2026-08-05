import react from "@vitejs/plugin-react"
import path from "path"
import { defineConfig } from "vite"

// 本番はVercel Function（api/[...path].ts）が /api を中継する。
// 開発サーバでも同じ同一オリジン構成にするため、Viteのプロキシで同じ経路を再現する。
const DEV_API_PROXY_TARGET = process.env.DEV_API_PROXY_TARGET ?? "http://localhost:8000"

export default defineConfig({
  plugins: [react()],
  resolve: {
    alias: {
      "@": path.resolve(__dirname, "./src"),
    },
  },
  server: {
    proxy: {
      "/api": DEV_API_PROXY_TARGET,
    },
  },
})
