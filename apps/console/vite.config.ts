import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import tailwindcss from "@tailwindcss/vite";
import path from "node:path";

/**
 * 工作台 SPA 构建配置。
 * dev 模式不在本配置启动：单端口由 server/index.ts（Hono + Vite middleware）承载，端口 3030。
 * 本配置仅用于 `vite build` 产出静态资源（prod 由同一 Node 进程托管）。
 */
export default defineConfig({
  plugins: [react(), tailwindcss()],
  resolve: {
    alias: { "@": path.resolve(__dirname, "src") },
  },
  build: {
    outDir: "dist",
    emptyOutDir: true,
    sourcemap: false,
    rollupOptions: {
      output: {
        // 稳定 vendor 独立 chunk：主包降到 500KB 以下 + 长缓存复用
        manualChunks: {
          react: ["react", "react-dom", "react-router-dom"],
          motion: ["motion"],
          virtual: ["@tanstack/react-virtual"],
        },
      },
    },
  },
  server: {
    port: 3030,
    // 开发代理：/api → API dev server（127.0.0.1:3031，SSE 经 http-proxy 流式透传）
    proxy: {
      "/api": { target: "http://127.0.0.1:3031", changeOrigin: true },
    },
  },
});
