// src/pages/PipelinePage.tsx — 流水线控制（SSE 实时日志台 · P2 全维度样板）
// 维度：D1 页入场 / D2 横幅退场 / D3 运行态脉冲 / D4 反馈 / D8 状态机 layout / D9 新日志
// 智能：L1 四态语义化 + 断连横幅；L2 失败/手动「问 AI 排障」（pendingPrompt 携日志跳 /assistant）
import { useNavigate } from "react-router-dom";
import { ConnectionBanner } from "@/components/pipeline/ConnectionBanner";
import { LogViewer } from "@/components/pipeline/LogViewer";
import { PipelineControls } from "@/components/pipeline/PipelineControls";
import { PipelineStatusBar } from "@/components/pipeline/PipelineStatusBar";
import { PageTransition } from "@/components/layout/PageTransition";
import { Badge } from "@/components/ui/badge";
import { usePipelineSSE } from "@/hooks/usePipelineSSE";
import { usePipelineStore } from "@/stores/pipelineSlice";
import { useChatStore } from "@/stores/chatSlice";

export default function PipelinePage() {
  usePipelineSSE();
  const navigate = useNavigate();
  const logs = usePipelineStore((s) => s.logs);
  const status = usePipelineStore((s) => s.status);
  const connected = usePipelineStore((s) => s.connected);
  const clearLogs = usePipelineStore((s) => s.clearLogs);

  const lastUpdated = logs.length ? logs[logs.length - 1].ts : (status?.endedAt ?? status?.startedAt ?? null);

  /** L2：把进程现场（批次/退出码/日志末 20 行）序列化进 chatSlice.pendingPrompt，跳助手自动发问 */
  const askAi = () => {
    const tail = usePipelineStore
      .getState()
      .logs.slice(-20)
      .map((l) => `${new Date(l.ts).toLocaleTimeString()} ${l.text}`)
      .join("\n");
    const prompt = [
      "【流水线排障请求】",
      status?.batch ? `批次：batch${status.batch}` : "",
      status?.state ? `当前状态：${status.state}` : "",
      status?.exitCode != null ? `退出码：${status.exitCode}` : "",
      "日志末 20 行：",
      tail || "（暂无日志）",
      "",
      "请按概率排序列出可能根因，并给出可立即执行的处置步骤（标注每步的验证命令/观察点）。",
    ]
      .filter((line) => line !== "")
      .join("\n");
    useChatStore.getState().setPendingPrompt(prompt);
    navigate("/assistant");
  };

  return (
    <PageTransition>
      <div className="space-y-5">
        <div className="flex items-center justify-between">
          <h1 className="text-xl font-bold">流水线控制 · 实时日志（SSE）</h1>
          <Badge variant={connected ? "success" : "muted"}>
            {connected ? "● 已连接" : "○ 重连中…"}
          </Badge>
        </div>

        <ConnectionBanner connected={connected} lastUpdated={lastUpdated} />

        <PipelineControls />
        <PipelineStatusBar status={status} onAskAi={askAi} />
        <LogViewer logs={logs} onClear={clearLogs} onAskAi={askAi} />
      </div>
    </PageTransition>
  );
}
