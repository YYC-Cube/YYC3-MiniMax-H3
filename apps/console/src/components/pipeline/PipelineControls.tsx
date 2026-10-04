// src/components/pipeline/PipelineControls.tsx — 触发面板（批次号 / 演练模式 / 状态徽章）
import { AlertTriangle, Play } from "lucide-react";
import { Badge, type BadgeProps } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { usePipelineStore } from "@/stores/pipelineSlice";
import type { RunStatus } from "@/lib/validators";

const STATE: Record<RunStatus["state"], { label: string; variant: BadgeProps["variant"] }> = {
  idle: { label: "空闲", variant: "muted" },
  running: { label: "运行中", variant: "running" },
  completed: { label: "已完成", variant: "success" },
  failed: { label: "失败", variant: "destructive" },
};

export function PipelineControls() {
  const status = usePipelineStore((s) => s.status);
  const batch = usePipelineStore((s) => s.batch);
  const dryRun = usePipelineStore((s) => s.dryRun);
  const triggering = usePipelineStore((s) => s.triggering);
  const triggerError = usePipelineStore((s) => s.triggerError);
  const setBatch = usePipelineStore((s) => s.setBatch);
  const setDryRun = usePipelineStore((s) => s.setDryRun);
  const trigger = usePipelineStore((s) => s.trigger);

  const running = status?.state === "running";
  const st = STATE[status?.state ?? "idle"];

  return (
    <Card>
      <CardContent className="flex flex-wrap items-end gap-4 pt-5">
        <div className="flex flex-col gap-1.5">
          <Label htmlFor="batch">批次号（留空=自动递增）</Label>
          <Input
            id="batch"
            value={batch}
            onChange={(e) => setBatch(e.target.value)}
            placeholder="如 03"
            className="mono w-32"
          />
        </div>
        <label className="flex items-center gap-2 pb-2 text-sm text-foreground">
          <input
            type="checkbox"
            checked={dryRun}
            onChange={(e) => setDryRun(e.target.checked)}
          />
          演练模式（不实际生成，联调用）
        </label>
        <Button onClick={() => void trigger()} disabled={running || triggering}>
          <Play />
          {running ? "运行中…" : "触发流水线"}
        </Button>
        <div className="ml-auto flex items-center gap-3 pb-1 text-sm">
          <span className="text-muted-foreground">状态：</span>
          <Badge variant={st.variant}>{st.label}</Badge>
          {status?.batch ? <span className="mono text-muted-foreground">batch{status.batch}</span> : null}
          {status?.exitCode != null ? (
            <span className="mono text-muted-foreground">exit={status.exitCode}</span>
          ) : null}
        </div>
      </CardContent>
      {triggerError ? (
        <CardContent className="flex items-center gap-2 pb-4 pt-0 text-sm text-destructive">
          <AlertTriangle className="size-4" />
          {triggerError}
        </CardContent>
      ) : null}
    </Card>
  );
}
