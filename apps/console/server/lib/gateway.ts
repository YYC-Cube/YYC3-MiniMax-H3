// server/lib/gateway.ts — 0379-World 网关客户端（服务端持有 X-API-Key，浏览器只经 console /api）
// Auth facts (core/api/middleware/auth.py L362): public endpoints accept API_KEYS or ADMIN_API_KEYS
export const GATEWAY_URL = (
  // Tailscale 地址（yyc3-45-1）——跨网络可达；LAN IP 192.168.3.45 仅同网段可用
  process.env.H3_GATEWAY_URL ?? "http://100.65.172.88:8000"
).replace(/\/$/, "");

const GATEWAY_KEY = process.env.H3_GATEWAY_API_KEY ?? "";

/** task id whitelist — same as video_task_runner.py（防队列投毒/路径穿越） */
export const TASK_ID_RE = /^[0-9a-f]{6,16}$/;

/** RequestInit（undici 类型）缺 cache 字段——显式扩展 */
type FetchInit = RequestInit & { cache?: "no-store" };

export function gatewayFetch(path: string, init?: FetchInit): Promise<Response> {
  const req: FetchInit = {
    ...init,
    headers: { "X-API-Key": GATEWAY_KEY, ...(init?.headers ?? {}) },
    cache: "no-store",
  };
  return fetch(`${GATEWAY_URL}${path}`, req);
}

export async function gatewayJson(
  path: string,
  init?: FetchInit
): Promise<{ ok: boolean; status: number; data: unknown }> {
  try {
    const r = await gatewayFetch(path, init);
    const data = await r.json().catch(() => null);
    return { ok: r.ok, status: r.status, data };
  } catch (e) {
    return { ok: false, status: 502, data: { error: `网关不可达: ${String(e)}` } };
  }
}
