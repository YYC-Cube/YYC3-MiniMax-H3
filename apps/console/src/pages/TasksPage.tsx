// src/pages/TasksPage.tsx — 任务中心（网关队列直连 + 10s 轮询）
import { useEffect } from "react";
import { RefreshCw } from "lucide-react";
import { PageTransition } from "@/components/layout/PageTransition";
import { TaskForm } from "@/components/tasks/TaskForm";
import { TaskItem } from "@/components/tasks/TaskItem";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { useTasksStore } from "@/stores/tasksSlice";

export default function TasksPage() {
  const tasks = useTasksStore((s) => s.tasks);
  const loaded = useTasksStore((s) => s.loaded);
  const loadError = useTasksStore((s) => s.loadError);
  const lastPoll = useTasksStore((s) => s.lastPoll);
  const load = useTasksStore((s) => s.load);

  // 10s 轮询（夜间 runner 领取后 queued→running→succeeded 自动上屏）
  useEffect(() => {
    void load();
    const t = setInterval(() => void load(), 10_000);
    return () => clearInterval(t);
  }, [load]);

  const running = tasks.filter((t) => t.status === "running").length;
  const queued = tasks.filter((t) => t.status === "queued").length;

  return (
    <PageTransition>
      <div className="mx-auto flex max-w-4xl flex-col gap-6">
        <div className="flex items-baseline gap-3">
          <h1 className="text-xl font-bold">任务中心</h1>
          <span className="text-sm text-muted-foreground">
            网关队列直连 · 排队 {queued} / 生成中 {running}
          </span>
          <span className="ml-auto flex items-center gap-2 text-xs text-muted-foreground">
            10s 自动刷新{lastPoll ? ` · 上次 ${new Date(lastPoll).toLocaleTimeString()}` : ""}
            <Button variant="ghost" size="icon" onClick={() => void load()} aria-label="立即刷新">
              <RefreshCw />
            </Button>
          </span>
        </div>

        <TaskForm />

        <section className="flex flex-col gap-2">
          {loadError && (
            <Card className="border-destructive/40">
              <CardContent className="pt-5 text-sm text-destructive">
                网关队列不可达：{loadError}
                （本地需 H3_GATEWAY_URL/H3_GATEWAY_API_KEY；部署需配置 TASKS_CLAIM_TOKEN）
              </CardContent>
            </Card>
          )}
          {loaded && !loadError && tasks.length === 0 && (
            <p className="text-sm text-muted-foreground">队列为空 — 提交第一个任务吧</p>
          )}
          {tasks.map((t) => (
            <TaskItem key={t.id} task={t} />
          ))}
        </section>
      </div>
    </PageTransition>
  );
}
