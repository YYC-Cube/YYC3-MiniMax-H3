// src/stores/pipelineSlice.ts — 流水线控制（触发 + SSE 日志 + 状态）
import { create } from "zustand";
import { triggerPipeline } from "@/lib/api";
import type { LogLine, RunStatus } from "@/lib/validators";

const MAX_LOGS = 2000;

interface PipelineState {
  status: RunStatus | null;
  logs: LogLine[];
  connected: boolean;
  batch: string;
  dryRun: boolean;
  triggerError: string | null;
  triggering: boolean;
  setStatus: (s: RunStatus) => void;
  appendLog: (l: LogLine) => void;
  setConnected: (c: boolean) => void;
  setBatch: (b: string) => void;
  setDryRun: (d: boolean) => void;
  clearLogs: () => void;
  trigger: () => Promise<void>;
}

export const usePipelineStore = create<PipelineState>()((set, get) => ({
  status: null,
  logs: [],
  connected: false,
  batch: "",
  dryRun: true,
  triggerError: null,
  triggering: false,

  setStatus: (s) => set({ status: s }),
  appendLog: (l) =>
    set((st) => ({ logs: st.logs.length >= MAX_LOGS ? [...st.logs.slice(-MAX_LOGS + 1), l] : [...st.logs, l] })),
  setConnected: (c) => set({ connected: c }),
  setBatch: (b) => set({ batch: b }),
  setDryRun: (d) => set({ dryRun: d }),
  clearLogs: () => set({ logs: [] }),

  trigger: async () => {
    if (get().status?.state === "running") return;
    set({ triggering: true, triggerError: null });
    try {
      await triggerPipeline(get().batch.trim() || null, get().dryRun);
    } catch (e) {
      set({ triggerError: e instanceof Error ? e.message : String(e) });
    } finally {
      set({ triggering: false });
    }
  },
}));
