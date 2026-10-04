// src/stores/tasksSlice.ts — 任务中心（网关队列代理）
import { create } from "zustand";
import { createTask, getTasks, type TaskSubmitInput } from "@/lib/api";
import type { TaskView } from "@/lib/validators";

interface TasksState {
  tasks: TaskView[];
  loaded: boolean;
  loadError: string | null;
  submitting: boolean;
  lastPoll: number | null;
  load: () => Promise<void>;
  submit: (input: TaskSubmitInput) => Promise<{ ok: boolean; id?: string; error?: string }>;
}

export const useTasksStore = create<TasksState>()((set) => ({
  tasks: [],
  loaded: false,
  loadError: null,
  submitting: false,
  lastPoll: null,

  load: async () => {
    try {
      const tasks = await getTasks();
      set({ tasks, loadError: null, lastPoll: Date.now(), loaded: true });
    } catch (e) {
      set({ loadError: e instanceof Error ? e.message : String(e), loaded: true });
    }
  },

  submit: async (input) => {
    set({ submitting: true });
    try {
      const created = await createTask(input);
      set({ submitting: false });
      return { ok: true, id: created.id };
    } catch (e) {
      set({ submitting: false });
      return { ok: false, error: e instanceof Error ? e.message : String(e) };
    }
  },
}));
