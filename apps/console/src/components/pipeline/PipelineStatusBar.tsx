// src/components/pipeline/PipelineStatusBar.tsx — 进程四态状态机条（L1 语义化）
// 契约真相：RunStatus.state = idle|running|completed|failed（进程级，非 Storyboard 六态）
// 动效：当前态 pill 共享 layoutId 滑动（D8）；运行中脉冲点（D3，reduced-motion 关闭）
import { Fragment, useEffect, useState } from "react";
import { motion } from "motion/react";
import { AlertTriangle, CheckCircle2, CircleDashed, Loader2, Sparkles } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { useMotionAllowed, useMotionCfg } from "@/components/motion/tokens";
import { cn } from "@/lib/utils";
import type { RunStatus } from "@/lib/validators";

type Tone = "idle" | "active" | "done" | "fail" | "dim";

const STEPS = [
  { key: "idle", label: "就绪", icon: CircleDashed },
  { key: "running", label: "运行中", icon: Loader2 },
  { key: "end", label: "完成", icon: CheckCircle2 },
] as const;

function toneOf(state: RunStatus["state"], index: number): Tone {
  const activeIndex = state === "idle" ? 0 : state === "running" ? 1 : 2;
  if (index > activeIndex) return "dim";
  if (index === 2 && state === "failed") return "fail";
  if (index === activeIndex) {
    if (state === "running") return "active";
    if (state === "completed") return "done";
    if (state === "failed") return "fail";
    return "idle";
  }
  return "done";
}

const PILL: Record<Tone, string> = {
  idle: "border-primary/40 bg-primary/10 text-primary",
  active: "border-sky-500/40 bg-sky-500/10 text-sky-400",
  done: "border-emerald-500/40 bg-emerald-500/10 text-emerald-400",
  fail: "border-destructive/50 bg-destructive/10 text-destructive",
  dim: "border-border bg-transparent text-muted-foreground",
};

/** mm:ss / h:mm:ss；running 时每秒刷新 */
function useElapsed(status: RunStatus | null): string | null {
  const [, tick] = useState(0);
  const state = status?.state;
  const startedAt = status?.startedAt ?? null;

  useEffect(() => {
    if (state !== "running" || !startedAt) return;
    const t = setInterval(() => tick((n) => n + 1), 1000);
    return () => clearInterval(t);
  }, [state, startedAt]);

  if (!status || !startedAt) return null;
  const end = state === "running" ? Date.now() : status.endedAt;
  if (!end) return null;
  const sec = Math.max(0, Math.round((end - startedAt) / 1000));
  const h = Math.floor(sec / 3600);
  const mm = String(Math.floor((sec % 3600) / 60)).padStart(2, "0");
  const ss = String(sec % 60).padStart(2, "0");
  return h > 0 ? `${h}:${mm}:${ss}` : `${mm}:${ss}`;
}

export function PipelineStatusBar({
  status,
  onAskAi,
}: {
  status: RunStatus | null;
  onAskAi: () => void;
}) {
  const state = status?.state ?? "idle";
  const elapsed = useElapsed(status);
  const motionAllowed = useMotionAllowed();
  const motionCfg = useMotionCfg();
  const failed = state === "failed";

  return (
    <Card>
      <CardContent className="flex flex-wrap items-center gap-x-6 gap-y-3 pt-5">
        {/* 步骤条：色+字+图标三编码 */}
        <ol
          className="flex items-center gap-2"
          aria-label={`流水线阶段：${STEPS[state === "failed" ? 2 : state === "completed" ? 2 : state === "running" ? 1 : 0].label}`}
        >
          {STEPS.map((step, i) => {
            const tone = toneOf(state, i);
            const Icon = failed && i === 2 ? AlertTriangle : step.icon;
            const isCurrent = tone === "active" || tone === "idle" || tone === "fail";
            return (
              <Fragment key={step.key}>
                <li
                  className={cn(
                    "relative flex items-center gap-1.5 rounded-full border px-3 py-1 text-xs font-medium transition-colors",
                    PILL[tone]
                  )}
                  aria-current={tone === "active" ? "step" : undefined}
                >
                  {isCurrent ? (
                    <motion.div
                      layoutId="pipeline-active-pill"
                      transition={motionCfg.spring}
                      className="pointer-events-none absolute inset-0 rounded-full ring-1 ring-primary/30"
                    />
                  ) : null}
                  <Icon
                    className={cn(
                      "size-3.5",
                      tone === "active" && motionAllowed && "animate-spin"
                    )}
                  />
                  <span className="relative">{failed && i === 2 ? "失败" : step.label}</span>
                  {tone === "active" && motionAllowed ? (
                    <span aria-hidden="true" className="relative flex size-1.5">
                      <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-sky-400 opacity-60" />
                      <span className="relative inline-flex size-1.5 rounded-full bg-sky-400" />
                    </span>
                  ) : null}
                </li>
                {i < STEPS.length - 1 ? (
                  <li
                    aria-hidden="true"
                    className={cn(
                      "h-px w-6",
                      tone === "dim" ? "bg-border" : failed && i === 1 ? "bg-destructive/50" : "bg-emerald-500/40"
                    )}
                  />
                ) : null}
              </Fragment>
            );
          })}
        </ol>

        {/* 元信息：批次 / 耗时 / 退出码 */}
        <div className="flex flex-wrap items-center gap-3 text-xs text-muted-foreground">
          {status?.batch ? <span className="mono">batch{status.batch}</span> : null}
          {elapsed ? <span className="mono">耗时 {elapsed}</span> : null}
          {failed && status?.exitCode != null ? (
            <span className="mono text-destructive">exit={status.exitCode}</span>
          ) : null}
          {failed ? (
            <span role="status" aria-live="polite">
              流水线异常退出，建议先看日志末段再处置
            </span>
          ) : null}
        </div>

        {failed ? (
          <Button variant="outline" size="sm" onClick={onAskAi} className="ml-auto border-primary/40 text-primary hover:bg-primary/10 hover:text-primary">
            <Sparkles />
            问 AI 排障（附日志末 20 行）
          </Button>
        ) : null}
      </CardContent>
    </Card>
  );
}
