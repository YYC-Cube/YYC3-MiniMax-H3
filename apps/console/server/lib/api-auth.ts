// server/lib/api-auth.ts — 共享鉴权（自 Next 路由平移，Hono Context 适配）
// 策略：令牌配置 → 常量时间比较（或合法会话令牌）；令牌缺省 → 仅回环/私网放行（运维便利）
import { timingSafeEqual } from "node:crypto";
import type { Context } from "hono";
import { getConnInfo } from "@hono/node-server/conninfo";
import { verifySession } from "./session.js";

function safeEqual(a: string, b: string): boolean {
  const ab = Buffer.from(a);
  const bb = Buffer.from(b);
  return ab.length === bb.length && timingSafeEqual(ab, bb);
}

/** 客户端 IP：优先 x-forwarded-for（反代场景），回退连接层地址 */
export function clientIp(c: Context): string {
  const xff = c.req.header("x-forwarded-for")?.split(",")[0]?.trim();
  if (xff) return xff;
  try {
    return getConnInfo(c).remote.address ?? "";
  } catch {
    return "";
  }
}

const LOOPBACK = new Set(["127.0.0.1", "::1", "::ffff:127.0.0.1", "0.0.0.0", "::ffff:0.0.0.0"]);

export function isLoopback(c: Context): boolean {
  return LOOPBACK.has(clientIp(c));
}

/** 私网/运营商级 NAT（Tailscale 100.64/10）——会话令牌签发范围（内网运维工具定位） */
const PRIVATE_V4 = /^(10\.|192\.168\.|172\.(1[6-9]|2\d|3[01])\.|100\.(6[4-9]|[7-9]\d)\.)/;

export function isPrivateNet(c: Context): boolean {
  const ip = clientIp(c);
  return isLoopback(c) || PRIVATE_V4.test(ip) || ip.startsWith("fd") || ip.startsWith("fe80");
}

/** 请求令牌校验：等于期望值（常量时间）或为合法会话令牌 */
function authorizeToken(provided: string | null | undefined, expected?: string): boolean {
  if (!provided) return false;
  if (expected && safeEqual(expected, provided)) return true;
  return verifySession(provided);
}

/** /api/tasks/**：TASKS_CLAIM_TOKEN（X-Claim-Token）或未配置时 loopback */
export function authorizeTasks(c: Context): boolean {
  const token = process.env.TASKS_CLAIM_TOKEN;
  if (token) return authorizeToken(c.req.header("x-claim-token"), token);
  return isLoopback(c);
}

/** /api/pipeline 与 /api/score：Bearer PIPELINE_TOKEN 或未配置时 loopback */
export function authorizePipeline(c: Context): boolean {
  const token = process.env.PIPELINE_TOKEN;
  if (token) {
    return authorizeToken((c.req.header("authorization") ?? "").replace(/^Bearer /, ""), token);
  }
  return isLoopback(c);
}
