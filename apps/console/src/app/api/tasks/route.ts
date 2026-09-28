// /api/tasks - gateway video task proxy (list GET / create POST).
// Server holds X-API-Key; browser auth via authorizeTasks (token or loopback).
// Create goes LAN-direct (H3_GATEWAY_URL) to avoid the public-chain 90s 499
// pitfall observed on 09-24 e2e with multipart uploads.
import { authorizeTasks } from "@/lib/api-auth";
import { gatewayJson } from "@/lib/gateway";
import { NextRequest, NextResponse } from "next/server";

export const dynamic = "force-dynamic";

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

export async function GET(req: NextRequest) {
  if (!authorizeTasks(req)) {
    return NextResponse.json({ error: "unauthorized" }, { status: 401 });
  }
  const { ok, status, data } = await gatewayJson("/v1/video/tasks?limit=50");
  return NextResponse.json(data, { status: ok ? 200 : status });
}

export async function POST(req: NextRequest) {
  if (!authorizeTasks(req)) {
    return NextResponse.json({ error: "unauthorized" }, { status: 401 });
  }

  let body: CreateBody;
  try {
    body = await req.json();
  } catch {
    return NextResponse.json({ error: "invalid json" }, { status: 400 });
  }

  const quality = body.quality ?? "preview";
  if (!VALID_QUALITY.has(quality)) {
    return NextResponse.json({ error: "quality 须为 preview/full" }, { status: 400 });
  }
  const prompt = body.prompt?.trim() || undefined;
  if (prompt && prompt.length > 4000) {
    return NextResponse.json({ error: "prompt ≤4000 字符" }, { status: 400 });
  }
  if (body.seed !== undefined && !(Number.isInteger(body.seed) && body.seed >= 0 && body.seed < 2 ** 31)) {
    return NextResponse.json({ error: "seed 须为 0~2^31-1 整数" }, { status: 400 });
  }
  if (body.refImageB64 && body.refImageB64.length > MAX_REF_B64) {
    return NextResponse.json({ error: "参考图过大（解码后须 ≤8MB）" }, { status: 413 });
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
  return NextResponse.json(data, { status: ok ? 201 : status });
}
