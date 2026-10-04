// server/routes/session.ts — /api/session：短时会话令牌签发
// 策略：私网/回环直接签发；否则需 X-Session-Key 匹配 H3_SESSION_KEY（fail-closed）
import { Hono } from "hono";
import { timingSafeEqual } from "node:crypto";
import { isPrivateNet } from "../lib/api-auth.js";
import { signSession } from "../lib/session.js";

export const sessionRoutes = new Hono();

function safeEqual(a: string, b: string): boolean {
  const ab = Buffer.from(a);
  const bb = Buffer.from(b);
  return ab.length === bb.length && timingSafeEqual(ab, bb);
}

sessionRoutes.get("/", (c) => {
  if (isPrivateNet(c)) return c.json({ token: signSession() });
  const key = process.env.H3_SESSION_KEY;
  if (key && safeEqual(c.req.header("x-session-key") ?? "", key)) {
    return c.json({ token: signSession() });
  }
  return c.json(
    { error: "会话签发仅限私网/回环；远程访问请配置 H3_SESSION_KEY 并携带 X-Session-Key" },
    401
  );
});
