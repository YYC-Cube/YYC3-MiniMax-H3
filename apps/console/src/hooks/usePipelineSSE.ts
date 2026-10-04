// src/hooks/usePipelineSSE.ts — 流水线 SSE（回填 + 实时日志 + 状态 + 文件变更）
import { useEffect } from "react";
import { createSSE } from "@/lib/sse";
import { logLineSchema, runStatusSchema, safeParseJson } from "@/lib/validators";
import { usePipelineStore } from "@/stores/pipelineSlice";

export function usePipelineSSE() {
  const setConnected = usePipelineStore((s) => s.setConnected);

  useEffect(() => {
    const dispose = createSSE({
      url: "/api/pipeline/stream",
      handlers: {
        state: (raw) => {
          const status = safeParseJson(raw, runStatusSchema);
          if (status) usePipelineStore.getState().setStatus(status);
        },
        log: (raw) => {
          const line = safeParseJson(raw, logLineSchema);
          if (line) usePipelineStore.getState().appendLog(line);
        },
      },
      onOpen: () => setConnected(true),
      onError: () => setConnected(false),
    });
    return dispose;
  }, [setConnected]);
}
