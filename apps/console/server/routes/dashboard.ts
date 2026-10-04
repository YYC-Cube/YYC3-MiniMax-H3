// server/routes/dashboard.ts — /api/dashboard：manifest 单一事实源 + 聚合桥（Vite SPA 的数据源等价物）
import { Hono } from "hono";
import { getDashboard } from "../lib/manifest.js";

export const dashboardRoutes = new Hono();

/** GET /api/dashboard — 只读数据（与旧 RSC 页面同权限姿态） */
dashboardRoutes.get("/", (c) => {
  return c.json(getDashboard());
});
