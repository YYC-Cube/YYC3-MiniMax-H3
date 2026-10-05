// server/routes/storyboard.ts — /api/storyboard：分镜确认闸门代理（agent 网关 8300，P1-1 对接）
// GET 状态（只读轮询）/ POST submit（漫剧侧或演示）/ POST confirm（人工选定→触发阶段4）
import { Hono, type Context } from "hono";
import { authorizePipeline } from "../lib/api-auth.js";

export const storyboardRoutes = new Hono();

const AGENT_URL = (process.env.H3_AGENT_URL ?? "http://127.0.0.1:8300").replace(/\/$/, "");

/** RequestInit（undici 类型）缺 cache 字段——显式扩展（同 server/lib/gateway.ts 先例） */
type FetchInit = RequestInit & { cache?: "no-store" };

/** agent 网关写操作鉴权：透传调用方 X-Claim-Token（issue_claim JSON）；
 *  console 层另有 authorizePipeline 门禁（Bearer/loopback）——双层各司其职 */
function claimHeaders(c: Context): Record<string, string> {
  const claim = c.req.header("x-claim-token");
  return claim ? { "X-Claim-Token": claim, "Content-Type": "application/json" } : { "Content-Type": "application/json" };
}

async function agentJson(path: string, init?: FetchInit): Promise<{ ok: boolean; status: number; data: unknown }> {
  const req: FetchInit = { ...init, cache: "no-store" };
  try {
    const r = await fetch(`${AGENT_URL}${path}`, req);
    const data = await r.json().catch(() => null);
    return { ok: r.ok, status: r.status, data };
  } catch (e) {
    return { ok: false, status: 502, data: { error: `agent 网关不可达: ${String(e)}` } };
  }
}

/** GET /api/storyboard — 闸门当前状态（候选/选定/StageStatus 六态） */
storyboardRoutes.get("/", async (c) => {
  const res = await agentJson("/api/stages/storyboard");
  return c.json(res.data, res.ok ? 200 : (res.status as 502));
});

/** POST /api/storyboard/submit — 提交分镜候选（body {batch, candidates[]}；演示/联调用） */
storyboardRoutes.post("/submit", async (c) => {
  if (!authorizePipeline(c)) return c.json({ error: "unauthorized" }, 401);
  const res = await agentJson("/api/stages/storyboard", {
    method: "POST",
    headers: claimHeaders(c),
    body: JSON.stringify(await c.req.json()),
  });
  return c.json(res.data, res.ok ? 200 : (res.status as 502));
});

/** POST /api/storyboard/confirm — 人工选定 → 触发阶段4（body {selected, asset_ref?, quality?, dry_run?}） */
storyboardRoutes.post("/confirm", async (c) => {
  if (!authorizePipeline(c)) return c.json({ error: "unauthorized" }, 401);
  const res = await agentJson("/api/stages/storyboard/confirm", {
    method: "POST",
    headers: claimHeaders(c),
    body: JSON.stringify(await c.req.json()),
  });
  return c.json(res.data, res.ok ? 200 : (res.status as 502));
});

// ---------------- /ref/* 静态：候选关键帧预览（只读 + 路径穿越防护） ----------------
import fs from "node:fs";
import path from "node:path";

const REF_ROOT = path.resolve(process.cwd(), "..", "..", "ref_images");
const MIME: Record<string, string> = {
  ".png": "image/png", ".jpg": "image/jpeg", ".jpeg": "image/jpeg", ".webp": "image/webp",
};

storyboardRoutes.get("/ref/*", (c: Context) => {
  const rel = c.req.path.replace(/^\/api\/storyboard\/ref\//, "");
  const file = path.resolve(REF_ROOT, rel);
  // 防穿越：resolve 后必须仍在 ref_images 内
  if (!file.startsWith(REF_ROOT + path.sep)) return c.json({ error: "非法路径" }, 400);
  if (!fs.existsSync(file) || !fs.statSync(file).isFile()) return c.json({ error: "not found" }, 404);
  const mime = MIME[path.extname(file).toLowerCase()];
  if (!mime) return c.json({ error: "仅支持图片" }, 400);
  return new Response(fs.readFileSync(file), {
    headers: { "Content-Type": mime, "Cache-Control": "no-store" },
  });
});
