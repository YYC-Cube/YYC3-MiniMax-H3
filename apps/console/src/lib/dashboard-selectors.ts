// src/lib/dashboard-selectors.ts — 仪表盘派生数据（行/徽章/KPI）
// 注：displayScore 与服务端 lib/manifest.ts 同构（纯函数，双端各自持有）
import type { Manifest } from "@yyc3/manifest-schema";

export function displayScore(
  rec: Manifest["records"][number]
): { score: number; source: "human" | "lipsync" | "none" } {
  if (rec.human?.score != null) return { score: rec.human.score, source: "human" };
  if (rec.lipsync?.score_norm != null)
    return { score: Math.round(rec.lipsync.score_norm * 100) / 10, source: "lipsync" };
  return { score: 0, source: "none" };
}

export type BatchRowBadge = "done" | "partial" | "failed" | "running";

export interface BatchRow {
  batch: string;
  model: string;
  startedAt: string;
  success: number;
  failed: number;
  skipped: number;
  avg: string;
  dur: string;
  badge: { text: string; title: string; tone: BatchRowBadge };
}

function scoresOf(m: Manifest): number[] {
  return m.records
    .filter((r) => r.status === "SUCCESS")
    .map(displayScore)
    .filter((s) => s.source !== "none")
    .map((s) => s.score);
}

export function batchRows(manifests: Manifest[]): BatchRow[] {
  return manifests.map((m) => {
    const success = m.records.filter((r) => r.status === "SUCCESS").length;
    const failed = m.records.filter((r) => r.status !== "SUCCESS" && r.status !== "SKIPPED").length;
    const skipped = m.records.filter((r) => r.status === "SKIPPED").length;
    const bs = scoresOf(m);
    const avg = bs.length ? (bs.reduce((a, b) => a + b, 0) / bs.length).toFixed(2) : "-";
    const dur =
      m.ended_at && m.started_at
        ? ((new Date(m.ended_at).getTime() - new Date(m.started_at).getTime()) / 60000).toFixed(1)
        : "-";

    const rc = m.reconciled;
    const badge: BatchRow["badge"] = m.ended_at
      ? { text: "完成", title: "", tone: "done" }
      : rc
        ? {
            text: rc.status === "partial" ? "部分完成" : "失败",
            title: `收敛于 ${rc.at} · 原因 ${rc.reason}（${rc.by}）`,
            tone: rc.status === "partial" ? "partial" : "failed",
          }
        : { text: "运行中", title: "", tone: "running" };

    return {
      batch: m.batch,
      model: `${m.model.variant.toUpperCase()} · ${m.model.pipeline}`,
      startedAt: m.started_at.replace("T", " ").slice(0, 16),
      success,
      failed,
      skipped,
      avg,
      dur,
      badge,
    };
  });
}
