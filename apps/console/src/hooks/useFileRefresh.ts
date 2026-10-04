// src/hooks/useFileRefresh.ts — SSE `file` 事件 → 800ms 去抖 → 仪表盘数据刷新
// （对齐旧 RSC router.refresh 的自动刷新体验；单例级连接由组件卸载管理）
import { useEffect, useRef } from "react";
import { createSSE } from "@/lib/sse";
import { useDashboardStore } from "@/stores/dashboardSlice";

const DEBOUNCE_MS = 800;

export function useFileRefresh() {
  const timerRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  useEffect(() => {
    const dispose = createSSE({
      url: "/api/pipeline/stream",
      handlers: {
        file: () => {
          if (!timerRef.current) {
            timerRef.current = setTimeout(() => {
              timerRef.current = null;
              void useDashboardStore.getState().load();
            }, DEBOUNCE_MS);
          }
        },
      },
    });
    return () => {
      dispose();
      if (timerRef.current) clearTimeout(timerRef.current);
    };
  }, []);
}
