// server/routes/tasks.ts — /api/tasks：网关视频任务代理（列表/创建/详情/结果流）
// 服务端持有 X-API-Key；浏览器鉴权经 authorizeTasks（令牌或回环）
// 创建走 LAN 直连（H3_GATEWAY_URL）规避公网链 90s 499 实证坑
import { Hono, type Context } from "hono";
import type { ContentfulStatusCode } from "hono/utils/http-status";
import { TASK_ID_RE, gatewayFetch, gatewayJson } from "../lib/gateway.js";
import { authorizeTasks } from "../lib/api-auth.js";

export const tasksRoutes = new Hono();

/** 网关响应透传（动态 status 收敛到 Hono 类型） */
function proxyJson(c: Context, res: { ok: boolean; status: number; data: unknown }) {
  return c.json(res.data, res.status as ContentfulStatusCode);
}

const VALID_QUALITY = new Set(["preview", "full"]);
// base64 膨胀 4/3：8MB 解码上限 ≈ 10.7M 字符
const MAX_REF_B64 = Math.ceil((8 * 1024 * 1024 * 4) / 3);

interface CreateBody {
  prompt?: string;
  quality?: string;
  seed?: number;
  refImageB64?: string;
  refImageName?: string;
}

/** GET /api/tasks — 列表 */
tasksRoutes.get("/", async (c) => {
  if (!authorizeTasks(c)) return c.json({ error: "unauthorized" }, 401);
  return proxyJson(c, await gatewayJson("/v1/video/tasks?limit=50"));
});

/** POST /api/tasks — 创建 */
tasksRoutes.post("/", async (c) => {
  if (!authorizeTasks(c)) return c.json({ error: "unauthorized" }, 401);

  let body: CreateBody;
  try {
    body = await c.req.json();
  } catch {
    return c.json({ error: "invalid json" }, 400);
  }

  const quality = body.quality ?? "preview";
  if (!VALID_QUALITY.has(quality)) {
    return c.json({ error: "quality 须为 preview/full" }, 400);
  }
  const prompt = body.prompt?.trim() || undefined;
  if (prompt && prompt.length > 4000) {
    return c.json({ error: "prompt ≤4000 字符" }, 400);
  }
  if (body.seed !== undefined && !(Number.isInteger(body.seed) && body.seed >= 0 && body.seed < 2 ** 31)) {
    return c.json({ error: "seed 须为 0~2^31-1 整数" }, 400);
  }
  if (body.refImageB64 && body.refImageB64.length > MAX_REF_B64) {
    return c.json({ error: "参考图过大（解码后须 ≤8MB）" }, 413);
  }

  // 字段名映射到网关契约（snake_case），prompt/seed 空值不传走 runner 默认
  const payload: Record<string, unknown> = { quality };
  if (prompt) payload.prompt = prompt;
  if (body.seed !== undefined) payload.seed = body.seed;
  if (body.refImageB64) {
    payload.ref_image_b64 = body.refImageB64;
    payload.ref_image_name = body.refImageName?.slice(0, 64) || "ref.png";
  }

  const { ok, status, data } = await gatewayJson("/v1/video/tasks", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  return c.json(data, (ok ? 201 : status) as ContentfulStatusCode);
});

/** GET /api/tasks/:id — 详情（轮询目标） */
tasksRoutes.get("/:id", async (c) => {
  if (!authorizeTasks(c)) return c.json({ error: "unauthorized" }, 401);
  const id = c.req.param("id");
  if (!TASK_ID_RE.test(id)) return c.json({ error: "非法任务 id" }, 400);
  return proxyJson(c, await gatewayJson(`/v1/video/tasks/${id}`));
});

/** GET /api/tasks/:id/result — mp4 流式代理（内联预览 / 下载） */
tasksRoutes.get("/:id/result", async (c) => {
  if (!authorizeTasks(c)) return c.json({ error: "unauthorized" }, 401);
  const id = c.req.param("id");
  if (!TASK_ID_RE.test(id)) return c.json({ error: "非法任务 id" }, 400);

  let upstream: Response;
  try {
    upstream = await gatewayFetch(`/v1/video/tasks/${id}/result`);
  } catch (e) {
    return c.json({ error: `网关不可达: ${String(e)}` }, 502);
  }
  if (!upstream.ok || !upstream.body) {
    const status = upstream.status === 404 || upstream.status === 410 ? upstream.status : 502;
    return c.json({ error: `结果不可用（网关 ${upstream.status}）` }, status);
  }

  return new Response(upstream.body, {
    headers: {
      "Content-Type": "video/mp4",
      "Content-Disposition": `inline; filename="yyc3_video_${id}.mp4"`,
      "Cache-Control": "no-store",
    },
  });
});
