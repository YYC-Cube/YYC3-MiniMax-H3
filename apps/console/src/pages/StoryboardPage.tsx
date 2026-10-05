// src/pages/StoryboardPage.tsx — 分镜确认闸门（P1-2，docs/18：候选 1-4 选图 → 触发阶段4）
// 交互范式复用精评抽屉：单选高亮 + 演练默认勾选（安全默认，真实生成显式取消）
import { useCallback, useEffect, useState } from "react";
import { Clapperboard, Loader2, RefreshCw, Send } from "lucide-react";
import { toast } from "sonner";
import { PageTransition } from "@/components/layout/PageTransition";
import { Badge, type BadgeProps } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { Label } from "@/components/ui/label";
import { cn } from "@/lib/utils";
import { confirmStoryboard, getStoryboard, submitStoryboard } from "@/lib/api";
import type { StoryboardStatus } from "@/lib/validators";

const STATUS_TONE: Record<string, { label: string; variant: BadgeProps["variant"] }> = {
  pending: { label: "待提交", variant: "muted" },
  waiting_feedback: { label: "等待确认", variant: "warning" },
  running: { label: "生成中", variant: "running" },
  passed: { label: "已通过", variant: "success" },
  rework: { label: "返工", variant: "destructive" },
  blocked: { label: "阻塞", variant: "destructive" },
};

export default function StoryboardPage() {
  const [status, setStatus] = useState<StoryboardStatus | null>(null);
  const [loadError, setLoadError] = useState<string | null>(null);
  const [selected, setSelected] = useState<string | null>(null);
  const [quality, setQuality] = useState<"" | "preview" | "full">("");
  const [dryRun, setDryRun] = useState(true);
  const [confirming, setConfirming] = useState(false);
  const [verdict, setVerdict] = useState<string | null>(null);

  const load = useCallback(async () => {
    try {
      const s = await getStoryboard();
      setStatus(s);
      setLoadError(null);
    } catch (e) {
      setLoadError(e instanceof Error ? e.message : String(e));
    }
  }, []);

  useEffect(() => {
    void load();
    const t = setInterval(() => void load(), 10_000);
    return () => clearInterval(t);
  }, [load]);

  const waiting = status?.status === "waiting_feedback";
  const tone = STATUS_TONE[status?.status ?? "pending"];

  const confirm = async () => {
    if (!selected) {
      toast.error("请先选定一张候选关键帧");
      return;
    }
    setConfirming(true);
    try {
      const res = await confirmStoryboard({
        selected,
        quality: quality || undefined,
        dry_run: dryRun,
      });
      setVerdict(res.verdict ?? "completed");
      toast.success(`阶段4 已触发（${dryRun ? "演练" : "真实"}${quality ? ` · ${quality}` : ""}）→ verdict: ${res.verdict ?? "-"}`);
      void load();
    } catch (e) {
      toast.error(e instanceof Error ? e.message : String(e));
    } finally {
      setConfirming(false);
    }
  };

  // 演示/联调：无闸门数据时可用当前资产库首个角色图快速提交（生产由漫剧侧提交）
  const demoSubmit = async () => {
    try {
      await submitStoryboard("99", ["characters/person_a.png"]);
      toast.success("已提交演示候选（batch99 · characters/person_a.png）");
      void load();
    } catch (e) {
      toast.error(e instanceof Error ? e.message : String(e));
    }
  };

  return (
    <PageTransition>
      <div className="mx-auto flex max-w-4xl flex-col gap-5">
        <div className="flex items-baseline gap-3">
          <h1 className="flex items-center gap-2 text-xl font-bold">
            <Clapperboard className="size-5 text-primary" />
            分镜确认闸门
          </h1>
          {tone ? <Badge variant={tone.variant}>{tone.label}</Badge> : null}
          {status?.batch ? <span className="mono text-sm text-muted-foreground">batch{status.batch}</span> : null}
          <span className="ml-auto flex items-center gap-2 text-xs text-muted-foreground">
            10s 自动刷新
            <Button variant="ghost" size="icon" onClick={() => void load()} aria-label="立即刷新">
              <RefreshCw />
            </Button>
          </span>
        </div>

        {loadError ? (
          <Card className="border-destructive/40">
            <CardContent className="pt-5 text-sm text-destructive">
              agent 网关不可达：{loadError}（需启动 uvicorn agent.h3_agent.gateway:app --port 8300）
            </CardContent>
          </Card>
        ) : null}

        {status && !waiting && (
          <Card>
            <CardContent className="flex flex-col items-start gap-3 pt-5 text-sm text-muted-foreground">
              <p>
                当前无待确认分镜（状态：{status.status}
                {status.selected ? ` · 已选定 ${status.selected}` : ""}）。
                漫剧侧经 <code className="mono text-xs">POST /api/stages/storyboard</code> 提交候选后，
                此页出现候选网格。
              </p>
              {verdict ? (
                <Badge variant={verdict === "passed" ? "success" : "warning"}>
                  最近确认结果 verdict: {verdict}
                </Badge>
              ) : null}
              <Button variant="outline" size="sm" onClick={() => void demoSubmit()}>
                演示：提交本地首个资产候选
              </Button>
            </CardContent>
          </Card>
        )}

        {status && waiting ? (
          <>
            <div className="grid grid-cols-2 gap-4 md:grid-cols-4" role="radiogroup" aria-label="分镜候选关键帧">
              {status.candidates.map((c) => (
                <button
                  key={c}
                  role="radio"
                  aria-checked={selected === c}
                  onClick={() => setSelected(c)}
                  className={cn(
                    "overflow-hidden rounded-xl border-2 transition-all focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring",
                    selected === c
                      ? "border-primary shadow-lg shadow-primary/20"
                      : "border-border hover:border-primary/50"
                  )}
                >
                  <img
                    src={`/api/storyboard/ref/${c}`}
                    alt={`分镜候选 ${c}`}
                    className="aspect-[9/16] w-full bg-secondary object-cover"
                    loading="lazy"
                  />
                  <div className="mono truncate px-2 py-1.5 text-left text-[10px] text-muted-foreground">{c}</div>
                </button>
              ))}
            </div>

            <Card>
              <CardContent className="flex flex-wrap items-end gap-4 pt-5">
                <div className="flex flex-col gap-1.5">
                  <Label htmlFor="sb-quality">档位（P2-2 pacing 驱动）</Label>
                  <select
                    id="sb-quality"
                    value={quality}
                    onChange={(e) => setQuality(e.target.value as "" | "preview" | "full")}
                    className="h-9 rounded-md border border-input bg-transparent px-3 text-sm focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
                  >
                    <option value="" className="bg-card">默认（引擎全质量）</option>
                    <option value="preview" className="bg-card">preview 快预览（360p/64帧/30步）</option>
                    <option value="full" className="bg-card">full 全质量</option>
                  </select>
                </div>
                <label className="flex items-center gap-2 pb-2 text-sm">
                  <input
                    type="checkbox"
                    checked={dryRun}
                    onChange={(e) => setDryRun(e.target.checked)}
                    className="size-4 rounded accent-primary focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
                  />
                  演练模式（安全默认）
                </label>
                <Button onClick={() => void confirm()} disabled={!selected || confirming} className="ml-auto">
                  {confirming ? (
                    <>
                      <Loader2 className="animate-spin" />
                      触发中…
                    </>
                  ) : (
                    <>
                      <Send />
                      确认选图并触发阶段4
                    </>
                  )}
                </Button>
              </CardContent>
            </Card>

            <p className="text-xs text-muted-foreground">
              确认即写 <code className="mono">asset_ref</code> 并触发阶段4 闭环（生成 → SyncNet 质检 → 打回/通过）；
              选图原则（OnlyShot）：静态图先锁构图——图迭代秒级，视频迭代 3.2h/条。
            </p>
          </>
        ) : null}
      </div>
    </PageTransition>
  );
}
