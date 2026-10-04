// server/lib/session.ts — 短时会话令牌（HMAC-SHA256 签名，12h TTL）
// 用途：SPA 在私网/带令牌部署下经 /api/session 换取令牌，附加到后续请求
// （X-Claim-Token / Bearer），满足「URL 传密钥永禁」铁律——令牌只存内存、不进 URL。
import { createHmac, timingSafeEqual } from "node:crypto";

const TTL_MS = 12 * 60 * 60 * 1000;
const FALLBACK_SECRET = "yyc3-console-dev-session-secret";

/** 参与签名的密钥集合：与 api-auth 的期望值同源；未配置时用开发回退（仅回环放行场景生效） */
export function sessionSecrets(): string[] {
  const secrets = [process.env.TASKS_CLAIM_TOKEN, process.env.PIPELINE_TOKEN].filter(
    (s): s is string => Boolean(s)
  );
  return secrets.length ? secrets : [FALLBACK_SECRET];
}

function b64url(buf: Buffer): string {
  return buf.toString("base64url");
}

export function signSession(): string {
  const payload = b64url(
    Buffer.from(JSON.stringify({ iat: Date.now(), exp: Date.now() + TTL_MS }))
  );
  const sig = sessionSecrets()
    .map((s) => b64url(createHmac("sha256", s).update(payload).digest()))
    .join(".");
  return `sess.${payload}.${sig}`;
}

/** 校验会话令牌：任一所配密钥签名通过即视为合法（常量时间比较） */
export function verifySession(token: string): boolean {
  if (!token.startsWith("sess.")) return false;
  const [, payload = "", sigs = ""] = token.split(".");
  try {
    const parsed = JSON.parse(Buffer.from(payload, "base64url").toString("utf-8"));
    if (typeof parsed.exp !== "number" || parsed.exp < Date.now()) return false;
  } catch {
    return false;
  }
  const secrets = sessionSecrets();
  const parts = sigs.split(".");
  for (let i = 0; i < secrets.length; i++) {
    const expected = b64url(createHmac("sha256", secrets[i]).update(payload).digest());
    const actual = parts[i];
    if (actual && expected.length === actual.length && timingSafeEqual(Buffer.from(expected), Buffer.from(actual))) {
      return true;
    }
  }
  return false;
}
