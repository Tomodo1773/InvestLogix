import react from "@vitejs/plugin-react"
import path from "path"
import { defineConfig } from "vite"

export default defineConfig({
  plugins: [react()],
  server: {
    // 本番のCloudflare Workerと同じ形にするためのdev proxy。
    // これによりフロントは常に同一オリジンの相対パスでAPIを叩ける。
    // docker composeではproxyを実行するのがwebコンテナ内のViteなので、
    // ホストのlocalhostではなくサービス名で解決する必要がある（API_PROXY_TARGET）
    proxy: {
      "/api": process.env.API_PROXY_TARGET ?? "http://localhost:8000",
    },
  },
  resolve: {
    alias: {
      "@": path.resolve(__dirname, "./src"),
    },
  },
})
