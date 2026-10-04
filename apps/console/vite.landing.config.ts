import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import tailwindcss from "@tailwindcss/vite";

/**
 * 落地页/文档站独立构建（GitHub Pages 快照部署，h3.yyc3.top）。
 * 与工作台 SPA 分离：落地页 = 曝光 + 预期管理 + 文档价值，不含 /api 交互。
 */
export default defineConfig({
  root: "landing",
  plugins: [react(), tailwindcss()],
  // 品牌图标沿用工作台 public 目录（favicon/yyc3-icons）
  publicDir: "../public",
  build: {
    outDir: "../dist-landing",
    emptyOutDir: true,
    sourcemap: false,
  },
});
