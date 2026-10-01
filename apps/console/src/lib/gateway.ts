// gateway.ts - server-side client for 0379-World gateway /v1/video/tasks (Phase 2.3).
// API key stays server-side; the browser only talks to console /api/tasks routes.
// Auth facts (core/api/middleware/auth.py L362): public endpoints accept
// API_KEYS or ADMIN_API_KEYS — the runner admin key works for local e2e.
export const GATEWAY_URL = (
  // Tailscale 地址（yyc3-45-1）——跨网络可达；LAN IP 192.168.3.45 仅同网段可用
  // （2026-10-01 事故：LAN 路径断导致 runner/面板误判 NAS 宕机，网关实际健康）
  process.env.H3_GATEWAY_URL ?? "http://100.65.172.88:8000"
).replace(/\/$/, "");

const GATEWAY_KEY = process.env.H3_GATEWAY_API_KEY ?? "";

/** task id whitelist — same as video_task_runner.py（防队列投毒/路径穿越） */
export const TASK_ID_RE = /^[0-9a-f]{6,16}$/;

export function gatewayFetch(path: string, init?: RequestInit): Promise<Response> {
  return fetch(`${GATEWAY_URL}${path}`, {
    ...init,
    headers: { "X-API-Key": GATEWAY_KEY, ...(init?.headers ?? {}) },
    cache: "no-store",
  });
}

export async function gatewayJson(path: string, init?: RequestInit): Promise<{
  ok: boolean;
  status: number;
  data: unknown;
}> {
  try {
    const r = await gatewayFetch(path, init);
    const data = await r.json().catch(() => null);
    return { ok: r.ok, status: r.status, data };
  } catch (e) {
    return { ok: false, status: 502, data: { error: `网关不可达: ${String(e)}` } };
  }
}
