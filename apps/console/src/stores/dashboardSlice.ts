// src/stores/dashboardSlice.ts — 仪表盘数据（manifest + 聚合桥）
import { create } from "zustand";
import { getDashboard } from "@/lib/api";
import type { DashboardData } from "@/lib/validators";

interface DashboardState {
  data: DashboardData | null;
  loading: boolean;
  error: string | null;
  lastUpdated: number | null;
  load: () => Promise<void>;
}

export const useDashboardStore = create<DashboardState>()((set) => ({
  data: null,
  loading: false,
  error: null,
  lastUpdated: null,
  load: async () => {
    set({ loading: true });
    try {
      const data = await getDashboard();
      set({ data, error: null, lastUpdated: Date.now(), loading: false });
    } catch (e) {
      set({ error: String(e), loading: false });
    }
  },
}));
