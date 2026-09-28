// /api/tasks/[id] - gateway task detail proxy (polling target).
import { NextRequest, NextResponse } from "next/server";
import { TASK_ID_RE, gatewayJson } from "@/lib/gateway";
import { authorizeTasks } from "@/lib/api-auth";

export const dynamic = "force-dynamic";

export async function GET(
  req: NextRequest,
  { params }: { params: Promise<{ id: string }> }
) {
  if (!authorizeTasks(req)) {
    return NextResponse.json({ error: "unauthorized" }, { status: 401 });
  }
  const { id } = await params;
  if (!TASK_ID_RE.test(id)) {
    return NextResponse.json({ error: "非法任务 id" }, { status: 400 });
  }
  const { ok, status, data } = await gatewayJson(`/v1/video/tasks/${id}`);
  return NextResponse.json(data, { status: ok ? 200 : status });
}
