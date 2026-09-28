// /api/tasks/[id]/result - streaming mp4 proxy (inline preview / download).
// Forwards gateway 404 (任务不存在/未成功) and 410 (结果过期) as-is.
import { NextRequest, NextResponse } from "next/server";
import { TASK_ID_RE, gatewayFetch } from "@/lib/gateway";
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

  let upstream: Response;
  try {
    upstream = await gatewayFetch(`/v1/video/tasks/${id}/result`);
  } catch (e) {
    return NextResponse.json({ error: `网关不可达: ${String(e)}` }, { status: 502 });
  }
  if (!upstream.ok || !upstream.body) {
    return NextResponse.json(
      { error: `结果不可用（网关 ${upstream.status}）` },
      { status: upstream.status === 404 || upstream.status === 410 ? upstream.status : 502 }
    );
  }

  return new Response(upstream.body, {
    headers: {
      "Content-Type": "video/mp4",
      "Content-Disposition": `inline; filename="yyc3_video_${id}.mp4"`,
      "Cache-Control": "no-store",
    },
  });
}
