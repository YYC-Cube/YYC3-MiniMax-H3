// src/components/tasks/TaskItem.tsx — 任务卡片（状态徽章 / 错误 / 视频预览与下载）
import { useEffect, useState } from "react";
import { ChevronDown, ChevronUp, Download, FileVideo, Loader2 } from "lucide-react";
import { Badge, type BadgeProps } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { apiFetch } from "@/lib/api";
import type { TaskView } from "@/lib/validators";

const STATUS: Record<TaskView["status"], { label: string; variant: BadgeProps["variant"] }> = {
  queued: { label: "排队中", variant: "muted" },
  running: { label: "生成中", variant: "running" },
  succeeded: { label: "已完成", variant: "success" },
  failed: { label: "失败", variant: "destructive" },
};

function fmtTime(ts: number | null | undefined): string {
  return ts ? new Date(ts * 1000).toLocaleString("zh-CN", { hour12: false }) : "-";
}

export function TaskItem({ task }: { task: TaskView }) {
  const [expanded, setExpanded] = useState(false);
  const [videoUrl, setVideoUrl] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const st = STATUS[task.status];

  useEffect(() => {
    return () => {
      if (videoUrl) URL.revokeObjectURL(videoUrl);
    };
  }, [videoUrl]);

  // 鉴权头无法注入 <video> 元素——用 apiFetch 拉 blob 再 objectURL（同时覆盖 Bearer 场景）
  const loadVideo = async () => {
    if (videoUrl) {
      setExpanded(!expanded);
      return;
    }
    setLoading(true);
    setError(null);
    try {
      const res = await apiFetch(`/api/tasks/${task.id}/result`);
      if (!res.ok) {
        const data: unknown = await res.json().catch(() => null);
        throw new Error((data as { error?: string } | null)?.error ?? `HTTP ${res.status}`);
      }
      const blob = await res.blob();
      setVideoUrl(URL.createObjectURL(blob));
      setExpanded(true);
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="rounded-lg border border-border p-3 text-sm">
      <div className="flex flex-wrap items-center gap-3">
        <Badge variant={st.variant}>{st.label}</Badge>
        <code className="mono text-xs">{task.id}</code>
        {task.quality ? <span className="text-xs text-muted-foreground">{task.quality}</span> : null}
        <span className="text-xs text-muted-foreground">创建 {fmtTime(task.created_at)}</span>
        {(task.attempts ?? 0) > 0 && (
          <span className="text-xs text-yellow-400">重试 ×{task.attempts}</span>
        )}
        {task.status === "succeeded" && (
          <Button variant="ghost" size="sm" className="ml-auto" onClick={() => void loadVideo()}>
            {loading ? (
              <Loader2 className="animate-spin" />
            ) : expanded ? (
              <ChevronUp />
            ) : (
              <ChevronDown />
            )}
            {expanded ? "收起" : "预览/下载"}
          </Button>
        )}
      </div>

      {task.error ? <p className="mt-2 text-xs text-destructive">{task.error}</p> : null}

      {expanded && task.status === "succeeded" && (
        <div className="mt-3 flex flex-col gap-2">
          {videoUrl ? (
            <>
              <video src={videoUrl} controls preload="metadata" className="w-72 rounded-md border border-border" />
              <a
                href={videoUrl}
                download={`yyc3_video_${task.id}.mp4`}
                className="flex items-center gap-1 text-xs text-primary underline"
              >
                <Download className="size-3.5" />
                下载 mp4{task.duration_seconds ? `（生成耗时 ${Math.round(task.duration_seconds / 60)}min）` : ""}
              </a>
            </>
          ) : (
            <span className="text-xs text-muted-foreground">
              <FileVideo className="mr-1 inline size-3.5" />
              加载视频中…
            </span>
          )}
          {task.archive_path ? (
            <span className="text-xs text-muted-foreground">NAS 持久副本：{task.archive_path}</span>
          ) : null}
        </div>
      )}

      {error ? <p className="mt-2 text-xs text-destructive">视频加载失败：{error}</p> : null}
    </div>
  );
}
