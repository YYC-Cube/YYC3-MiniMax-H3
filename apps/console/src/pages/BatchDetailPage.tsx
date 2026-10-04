// src/pages/BatchDetailPage.tsx — 批次详情（视频卡片网格 + 人工精评抽屉）
import { Link, useParams } from "react-router-dom";
import { ArrowLeft, Loader2 } from "lucide-react";
import { PageTransition } from "@/components/layout/PageTransition";
import { RefineDrawer } from "@/components/batches/RefineDrawer";
import { Card, CardContent } from "@/components/ui/card";
import { useDashboardData } from "@/hooks/useDashboardData";
import { displayScore } from "@/lib/dashboard-selectors";

export default function BatchDetailPage() {
  const { id: rawId } = useParams();
  const { data, loading } = useDashboardData();

  const batch = (rawId ?? "").replace(/^batch/i, "").padStart(2, "0");
  const manifest = data?.manifests.find((m) => m.batch === batch);

  if (loading && !data) {
    return (
      <div className="flex items-center gap-2 py-16 text-muted-foreground">
        <Loader2 className="animate-spin" />
        加载批次数据…
      </div>
    );
  }

  if (!manifest) {
    return (
      <div className="space-y-4">
        <Link to="/" className="flex items-center gap-1 text-sm text-muted-foreground hover:text-foreground">
          <ArrowLeft className="size-4" />
          返回仪表盘
        </Link>
        <Card>
          <CardContent className="pt-5 text-muted-foreground">未找到 batch{batch} 的 manifest.json</CardContent>
        </Card>
      </div>
    );
  }

  const success = manifest.records.filter((r) => r.status === "SUCCESS");

  return (
    <PageTransition>
      <div className="space-y-5">
        <Link to="/" className="flex items-center gap-1 text-sm text-muted-foreground hover:text-foreground">
          <ArrowLeft className="size-4" />
          返回仪表盘
        </Link>
        <div className="flex items-baseline gap-4">
          <h1 className="text-xl font-bold">batch{batch} 批次详情</h1>
          <span className="mono text-sm text-muted-foreground">
            {manifest.model.variant.toUpperCase()} · {success.length}/{manifest.records.length} 成功 ·
            {manifest.started_at.replace("T", " ").slice(0, 16)} 启动
          </span>
        </div>

        <div className="grid grid-cols-1 gap-4 md:grid-cols-2 xl:grid-cols-3">
          {success.map((r) => {
            const { score, source } = displayScore(r);
            return (
              <Card key={`${r.ref_img}-${r.seed}`}>
                <CardContent className="space-y-2 pt-5">
                  <div className="flex items-center justify-between">
                    <span className="mono text-sm font-bold text-primary">seed {r.seed}</span>
                    <span className="mono text-sm">
                      {score > 0 ? `${score}/10` : "待精评"}
                      <span className="ml-1 text-xs text-muted-foreground">
                        {source === "lipsync" ? "自动" : source === "human" ? "人工" : ""}
                      </span>
                    </span>
                  </div>
                  <div className="mono text-xs text-muted-foreground">{r.ref_img}</div>
                  <div className="mono text-xs text-muted-foreground">
                    {r.gen_seconds ? `${r.gen_seconds.toFixed(0)}s` : "-"} ·{" "}
                    {r.peak_rss_gb ? `${r.peak_rss_gb.toFixed(1)}GB` : "-"}
                    {r.lipsync?.av_offset != null ? ` · offset ${r.lipsync.av_offset.toFixed(3)}` : ""}
                  </div>
                  <div className="mono break-all text-[10px] text-muted-foreground opacity-70">
                    {r.video_path}
                  </div>
                  <RefineDrawer
                    batch={batch}
                    refImg={r.ref_img}
                    seed={r.seed}
                    initialScore={r.human?.score ?? null}
                    initialTags={r.human?.tags ?? ""}
                  />
                </CardContent>
              </Card>
            );
          })}
        </div>
      </div>
    </PageTransition>
  );
}
