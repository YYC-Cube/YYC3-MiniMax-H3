// api-auth.ts - shared auth helpers for console API routes.
// Policy mirrors /api/pipeline/run: token configured → constant-time header
// match; token absent → loopback only（本机/局域网运维便利）.
import { timingSafeEqual } from "node:crypto";
import { NextRequest } from "next/server";

function isLoopback(req: NextRequest): boolean {
  return ["127.0.0.1", "::1", "::ffff:127.0.0.1"].includes(
    req.headers.get("x-forwarded-for")?.split(",")[0]?.trim() ?? ""
  );
}

function safeEqual(a: string, b: string): boolean {
  const ab = Buffer.from(a);
  const bb = Buffer.from(b);
  return ab.length === bb.length && timingSafeEqual(ab, bb);
}

/** /api/tasks/**：TASKS_CLAIM_TOKEN（X-Claim-Token）或未配置时 loopback */
export function authorizeTasks(req: NextRequest): boolean {
  const token = process.env.TASKS_CLAIM_TOKEN;
  if (!token) return isLoopback(req);
  return safeEqual(token, req.headers.get("x-claim-token") ?? "");
}

/** /api/score 补齐：与 /api/pipeline/run 完全同策略（Bearer PIPELINE_TOKEN 或 loopback） */
export function authorizePipeline(req: NextRequest): boolean {
  const token = process.env.PIPELINE_TOKEN;
  if (token) {
    return safeEqual(
      token,
      (req.headers.get("authorization") ?? "").replace(/^Bearer /, "")
    );
  }
  return isLoopback(req);
}
