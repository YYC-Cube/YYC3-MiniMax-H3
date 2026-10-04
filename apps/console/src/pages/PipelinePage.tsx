// src/pages/PipelinePage.tsx — 流水线控制（SSE 实时日志台）
import { LogViewer } from "@/components/pipeline/LogViewer";
import { PipelineControls } from "@/components/pipeline/PipelineControls";
import { PageTransition } from "@/components/layout/PageTransition";
import { Badge } from "@/components/ui/badge";
import { usePipelineSSE } from "@/hooks/usePipelineSSE";
import { usePipelineStore } from "@/stores/pipelineSlice";

export default function PipelinePage() {
  usePipelineSSE();
  const logs = usePipelineStore((s) => s.logs);
  const connected = usePipelineStore((s) => s.connected);
  const clearLogs = usePipelineStore((s) => s.clearLogs);

  return (
    <PageTransition>
      <div className="space-y-5">
        <div className="flex items-center justify-between">
          <h1 className="text-xl font-bold">流水线控制 · 实时日志（SSE）</h1>
          <Badge variant={connected ? "success" : "muted"}>
            {connected ? "● 已连接" : "○ 重连中…"}
          </Badge>
        </div>
        <PipelineControls />
        <LogViewer logs={logs} onClear={clearLogs} />
      </div>
    </PageTransition>
  );
}
