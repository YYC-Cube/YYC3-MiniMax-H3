// src/hooks/useDashboardData.ts — 仪表盘数据加载（挂载即取 + 订阅文件变更自动刷新）
import { useEffect } from "react";
import { useDashboardStore } from "@/stores/dashboardSlice";
import { useFileRefresh } from "./useFileRefresh";

export function useDashboardData() {
  const load = useDashboardStore((s) => s.load);
  const data = useDashboardStore((s) => s.data);
  const loading = useDashboardStore((s) => s.loading);
  const error = useDashboardStore((s) => s.error);
  const lastUpdated = useDashboardStore((s) => s.lastUpdated);

  useFileRefresh();

  useEffect(() => {
    void load();
  }, [load]);

  return { data, loading, error, lastUpdated };
}
