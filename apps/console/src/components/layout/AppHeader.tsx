// src/components/layout/AppHeader.tsx — 顶栏（品牌 + 导航 + 在线状态）
import { NavLink } from "react-router-dom";
import { LayoutDashboard, ListTodo, Sparkles, Workflow } from "lucide-react";
import { cn } from "@/lib/utils";
import { Badge } from "@/components/ui/badge";
import { usePipelineStore } from "@/stores/pipelineSlice";

const NAV = [
  { to: "/", label: "仪表盘", icon: LayoutDashboard, end: true },
  { to: "/pipeline", label: "流水线", icon: Workflow, end: false },
  { to: "/tasks", label: "任务中心", icon: ListTodo, end: false },
  { to: "/assistant", label: "AI 助手", icon: Sparkles, end: false },
] as const;

export function AppHeader() {
  const connected = usePipelineStore((s) => s.connected);

  return (
    <header className="sticky top-0 z-40 border-b border-border bg-background/80 backdrop-blur">
      <div className="mx-auto flex h-14 max-w-[1440px] items-center gap-6 px-6">
        <img
          src="/yyc3-icons/Web App/favicon-32.png"
          alt="YYC³ 品牌图标"
          width={24}
          height={24}
          className="rounded"
        />
        <span className="text-lg font-bold text-primary">YYC³ MiniMax-H3</span>
        <nav aria-label="主导航" className="flex items-center gap-1 text-sm">
          {NAV.map(({ to, label, icon: Icon, end }) => (
            <NavLink
              key={to}
              to={to}
              end={end}
              className={({ isActive }) =>
                cn(
                  "flex items-center gap-1.5 rounded-md px-3 py-1.5 transition-colors",
                  isActive
                    ? "bg-secondary text-foreground"
                    : "text-muted-foreground hover:bg-secondary/60 hover:text-foreground"
                )
              }
            >
              <Icon className="size-4" />
              {label}
            </NavLink>
          ))}
        </nav>
        <div className="ml-auto flex items-center gap-3">
          {connected ? (
            <Badge variant="success">
              <span aria-hidden="true" className="relative flex size-1.5">
                <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-emerald-400 opacity-60" />
                <span className="relative inline-flex size-1.5 rounded-full bg-emerald-400" />
              </span>
              SSE 在线
            </Badge>
          ) : (
            <Badge variant="muted">SSE 离线</Badge>
          )}
          <span className="text-xs text-muted-foreground">Vite 6 · React 19</span>
        </div>
      </div>
    </header>
  );
}
