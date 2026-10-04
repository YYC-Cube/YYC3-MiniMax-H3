// server/index.ts — 单端口入口
// prod：NODE_ENV=production 时同进程托管 /api + dist 静态资源 + SPA fallback（端口 3030）
// dev：tsx watch 仅起 API（127.0.0.1:3031），Vite dev（3030，/api 代理）由 scripts/dev.mjs 拉起
import { serve } from "@hono/node-server";
import { serveStatic } from "@hono/node-server/serve-static";
import { Hono } from "hono";
import fs from "node:fs";
import path from "node:path";
import { dashboardRoutes } from "./routes/dashboard.js";
import { pipelineRoutes } from "./routes/pipeline.js";
import { tasksRoutes } from "./routes/tasks.js";
import { scoreRoutes } from "./routes/score.js";
import { chatRoutes } from "./routes/chat.js";
import { sessionRoutes } from "./routes/session.js";

const isProd = process.env.NODE_ENV === "production";
const PORT = Number(process.env.CONSOLE_PORT ?? 3030);
const API_PORT = Number(process.env.CONSOLE_API_PORT ?? 3031);

const app = new Hono();

// ---- 健康检查（供冒烟/运维轮询）----
app.get("/api/health", (c) => c.json({ ok: true, ts: Date.now(), mode: isProd ? "prod" : "dev" }));

// ---- 业务路由 ----
app.route("/api/dashboard", dashboardRoutes);
app.route("/api/pipeline", pipelineRoutes);
app.route("/api/tasks", tasksRoutes);
app.route("/api/score", scoreRoutes);
app.route("/api/chat", chatRoutes);
app.route("/api/session", sessionRoutes);

app.notFound((c) =>
  c.req.path.startsWith("/api") ? c.json({ error: "not found" }, 404) : c.text("Not Found", 404)
);

if (isProd) {
  // ---- 生产：静态资源 + SPA fallback（单进程单端口）----
  const distDir = path.resolve(process.cwd(), "dist");
  app.use("/assets/*", serveStatic({ root: distDir }));
  app.use("/yyc3-icons/*", serveStatic({ root: distDir }));
  app.use("/favicon.ico", serveStatic({ root: distDir }));

  app.use("*", async (c, next) => {
    if (c.req.path.startsWith("/api")) return next();
    const filePath = path.join(distDir, c.req.path.slice(1));
    if (fs.existsSync(filePath) && fs.statSync(filePath).isFile()) {
      return serveStatic({ root: distDir })(c, next);
    }
    const html = fs.readFileSync(path.join(distDir, "index.html"), "utf-8");
    return c.html(html);
  });

  serve({ fetch: app.fetch, port: PORT });
  console.log(`[console] prod 模式：http://0.0.0.0:${PORT}（/api + 静态资源）`);
} else {
  // ---- 开发：仅 API，绑 127.0.0.1（Vite 3030 代理到本端口）----
  serve({ fetch: app.fetch, port: API_PORT, hostname: "127.0.0.1" });
  console.log(`[console] API dev server → http://127.0.0.1:${API_PORT}`);
}
