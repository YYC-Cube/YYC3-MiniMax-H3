// server/routes/pipeline.ts — /api/pipeline：状态查询 + 触发 + SSE 实时流
import { Hono } from "hono";
import { streamSSE } from "hono/streaming";
import { pipelineManager, type FileChange, type LogLine } from "../lib/pipeline-manager.js";
import { authorizePipeline } from "../lib/api-auth.js";

export const pipelineRoutes = new Hono();

const HEARTBEAT_MS = 15_000;
const STATE_POLL_MS = 2_000;

pipelineRoutes.get("/stream", (c) =>
  streamSSE(c, async (stream) => {
    let unsubLogs: (() => void) | null = null;
    let unsubFiles: (() => void) | null = null;
    let heartbeat: ReturnType<typeof setInterval> | null = null;
    let stateTimer: ReturnType<typeof setInterval> | null = null;
    let lastState = "";

    const write = (event: string, data: unknown) => {
      stream.writeSSE({ event, data: JSON.stringify(data) }).catch(() => {
        /* 客户端断开 → onAbort 清理 */
      });
    };

    try {
      // 1) 回填（断线重连不丢上下文）
      const { status, logs } = pipelineManager.replay();
      lastState = status.state;
      write("state", status);
      for (const line of logs) write("log", line);

      // 2) 实时订阅（日志 + 文件变更）
      unsubLogs = pipelineManager.subscribe((line: LogLine) => write("log", line));
      unsubFiles = pipelineManager.subscribeFiles((change: FileChange) => write("file", change));

      // 3) 状态轮询广播（manager 内部 close → completed/failed）
      stateTimer = setInterval(() => {
        const cur = pipelineManager.getStatus();
        if (cur.state !== lastState) {
          lastState = cur.state;
          write("state", cur);
        }
      }, STATE_POLL_MS);

      // 4) 心跳（代理/客户端保活）
      heartbeat = setInterval(() => write("heartbeat", {}), HEARTBEAT_MS);

      // 5) 断开清理
      stream.onAbort(() => {
        if (heartbeat) clearInterval(heartbeat);
        if (stateTimer) clearInterval(stateTimer);
        unsubLogs?.();
        unsubFiles?.();
      });

      // 挂起：连接存活即持续推流
      await new Promise<void>(() => {});
    } finally {
      // 兜底清理（避免流异常退出时泄漏订阅）
      if (heartbeat) clearInterval(heartbeat);
      if (stateTimer) clearInterval(stateTimer);
      unsubLogs?.();
      unsubFiles?.();
    }
  })
);

/** GET /api/pipeline — 当前运行状态 */
pipelineRoutes.get("/", (c) => {
  if (!authorizePipeline(c)) return c.json({ error: "unauthorized" }, 401);
  return c.json(pipelineManager.getStatus());
});

/** POST /api/pipeline/run — 触发流水线（spawn 白名单 + 单飞锁） */
pipelineRoutes.post("/run", async (c) => {
  if (!authorizePipeline(c)) return c.json({ error: "unauthorized" }, 401);
  let body: { batch?: string | null; dryRun?: boolean } = {};
  try {
    body = await c.req.json();
  } catch {
    // 空 body 允许：批次自动递增
  }
  const result = pipelineManager.start(body.batch ?? null, body.dryRun === true);
  if (!result.ok) return c.json({ error: result.error }, 409);
  return c.json({ started: true, batch: result.batch, status: pipelineManager.getStatus() });
});
