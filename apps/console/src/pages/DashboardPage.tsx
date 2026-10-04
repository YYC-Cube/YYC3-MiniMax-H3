// src/pages/DashboardPage.tsx — 仪表盘：KPI + 聚合卡 + 趋势 + 批次明细
import { AlertTriangle, BarChart3, Layers, TrendingUp } from "lucide-react";
import { BatchesTable } from "@/components/dashboard/BatchesTable";
import { StatCard } from "@/components/dashboard/StatCard";
import { TrendChart } from "@/components/dashboard/TrendChart";
import { PageTransition } from "@/components/layout/PageTransition";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent } from "@/components/ui/card";
import { useDashboardData } from "@/hooks/useDashboardData";
import { displayScore } from "@/lib/dashboard-selectors";

export default function DashboardPage() {
  const { data, loading, error, lastUpdated } = useDashboardData();
  const manifests = data?.manifests ?? [];
  const payload = data?.payload;

  const totalRecords = manifests.reduce((n, m) => n + m.records.length, 0);
  const successRecords = manifests.reduce(
    (n, m) => n + m.records.filter((r) => r.status === "SUCCESS").length,
    0
  );
  const scores = manifests
    .flatMap((m) => m.records.filter((r) => r.status === "SUCCESS").map(displayScore))
    .filter((s) => s.source !== "none");
  const avg = scores.length ? (scores.reduce((a, s) => a + s.score, 0) / scores.length).toFixed(2) : "-";
  const top = payload?.top10?.[0];

  const bs = payload?.batches ?? [];
  const completedN = bs.filter((b) => b.status === "completed").length;
  const abnormalN = bs.filter((b) => b.status === "partial" || b.status === "failed").length;
  const runningN = bs.filter((b) => b.status === "running").length;
  const clipW = bs.reduce((n, b) => n + b.success, 0);
  const weightedAvg = clipW
    ? (bs.reduce((a, b) => a + b.avgScore * b.success, 0) / clipW).toFixed(2)
    : "-";
  const totalHours = bs.length
    ? (bs.reduce((a, b) => a + (b.durationMin ?? 0), 0) / 60).toFixed(1)
    : "-";
  const topDefect = Object.entries(
    bs.reduce<Record<string, number>>((acc, b) => {
      for (const [k, v] of Object.entries(b.defects)) acc[k] = (acc[k] ?? 0) + v;
      return acc;
    }, {})
  ).sort((x, y) => y[1] - x[1])[0];
  const trend = bs
    .slice()
    .sort((a, b) => a.time.localeCompare(b.time))
    .map((b) => ({ label: b.id, score: b.avgScore }));

  return (
    <PageTransition>
      <div className="space-y-6">
        <section className="flex items-baseline justify-between">
          <h1 className="text-xl font-bold">仪表盘 · 单一事实源直读</h1>
          <span className="text-xs text-muted-foreground">
            {loading ? "加载中…" : lastUpdated ? `更新于 ${new Date(lastUpdated).toLocaleTimeString()}` : "未加载"}
          </span>
        </section>

        {error ? (
          <Card className="border-destructive/40">
            <CardContent className="flex items-center gap-2 pt-5 text-destructive">
              <AlertTriangle className="size-4" />
              数据服务不可达：{error}
            </CardContent>
          </Card>
        ) : null}

        {data ? (
          <>
            <section>
              <div className="grid grid-cols-2 gap-4 md:grid-cols-4">
                <StatCard label="批次总数" value={String(manifests.length)} icon={<Layers className="size-3.5" />} />
                <StatCard
                  label="生成记录"
                  value={`${successRecords}/${totalRecords}`}
                  hint="SUCCESS / 全部"
                />
                <StatCard
                  label="平均分（0-10）"
                  value={avg}
                  hint="human 优先，lipsync×10 回退"
                  icon={<TrendingUp className="size-3.5" />}
                />
                <StatCard
                  label="Top1"
                  value={top ? `${top.seed}` : "-"}
                  hint={top ? `${top.batch} · ${top.score} 分` : "暂无"}
                />
              </div>
            </section>

            {payload ? (
              <section>
                <div className="mb-3 flex items-center gap-3">
                  <h2 className="font-semibold">批次聚合</h2>
                  <Badge variant="outline" className="mono">
                    contract v{payload.schema_version} · {payload.generated_at} 导出
                  </Badge>
                </div>
                <div className="grid grid-cols-2 gap-4 md:grid-cols-4">
                  <StatCard
                    label="完成 / 异常 / 运行"
                    value={`${completedN} / ${abnormalN} / ${runningN}`}
                    hint={abnormalN > 0 ? "异常=partial/failed（含僵尸收敛）" : undefined}
                  />
                  <StatCard
                    label="加权均分（0-10）"
                    value={weightedAvg}
                    hint="按成功 clip 数加权"
                  />
                  <StatCard label="累计耗时（h）" value={totalHours} />
                  <StatCard
                    label="Top 缺陷"
                    value={topDefect ? topDefect[0] : "-"}
                    hint={topDefect ? `累计 ${topDefect[1]} 次` : "暂无缺陷标签"}
                  />
                </div>
                {trend.length > 1 ? (
                  <Card className="mt-4">
                    <CardContent className="pt-5">
                      <div className="mb-2 flex items-center gap-2 text-xs text-muted-foreground">
                        <BarChart3 className="size-3.5" />
                        批次均分趋势（0-10，按开始时间排序）
                      </div>
                      <TrendChart points={trend} />
                    </CardContent>
                  </Card>
                ) : null}
              </section>
            ) : null}

            {data.errors.length > 0 ? (
              <Card className="border-yellow-700">
                <CardContent className="pt-5">
                  <div className="text-sm text-yellow-400">⚠ schema 校验警告（双端契约漂移检查）</div>
                  <ul className="mono mt-2 space-y-1 text-xs text-muted-foreground">
                    {data.errors.map((e) => (
                      <li key={e}>{e}</li>
                    ))}
                  </ul>
                </CardContent>
              </Card>
            ) : null}

            <section>
              <h2 className="mb-3 font-semibold">批次明细（manifest.json 直读）</h2>
              <BatchesTable manifests={manifests} />
            </section>

            <section className="text-xs text-muted-foreground">
              数据链路：scripts/pipeline-tools（Python 引擎写 manifest）→ console-server /api/dashboard →
              本页 Zustand store。SSE `file` 事件驱动自动刷新（500ms 服务端去抖 + 800ms 客户端去抖）。
            </section>
          </>
        ) : !loading ? (
          <Card>
            <CardContent className="pt-5 text-muted-foreground">
              暂无数据 —— 先运行 pipeline_auto.py 生成 manifest。
            </CardContent>
          </Card>
        ) : null}
      </div>
    </PageTransition>
  );
}
