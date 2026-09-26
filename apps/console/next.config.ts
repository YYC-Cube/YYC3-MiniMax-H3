import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  // 多 lockfile 环境下显式锚定追踪根（否则 Next 可能推断到 ~/ 导致路径越界）
  outputFileTracingRoot: __dirname,
  // PAGES_EXPORT=1 时进入静态导出（GitHub Pages 快照部署 workflows/pages.yml）；
  // 本地 dev/build 与生产保持默认模式（API 路由仅在非导出模式可用）
  output: process.env.PAGES_EXPORT ? "export" : undefined,
};

export default nextConfig;
