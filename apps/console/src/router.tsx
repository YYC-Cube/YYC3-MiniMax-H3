// src/router.tsx — 应用路由（react-router v7；AI 助手懒加载：AI SDK 体积不拖累主包）
import { lazy, Suspense } from "react";
import { createBrowserRouter, Navigate } from "react-router-dom";
import App from "@/App";
import BatchDetailPage from "@/pages/BatchDetailPage";
import DashboardPage from "@/pages/DashboardPage";
import PipelinePage from "@/pages/PipelinePage";
import TasksPage from "@/pages/TasksPage";
import { Loader2 } from "lucide-react";

const AssistantPage = lazy(() => import("@/pages/AssistantPage"));

function AssistantFallback() {
  return (
    <div className="flex items-center gap-2 py-16 text-muted-foreground">
      <Loader2 className="animate-spin" />
      加载 AI 助手…
    </div>
  );
}

export const router = createBrowserRouter([
  {
    element: <App />,
    children: [
      { path: "/", element: <DashboardPage /> },
      { path: "/pipeline", element: <PipelinePage /> },
      { path: "/tasks", element: <TasksPage /> },
      { path: "/batches/:id", element: <BatchDetailPage /> },
      {
        path: "/assistant",
        element: (
          <Suspense fallback={<AssistantFallback />}>
            <AssistantPage />
          </Suspense>
        ),
      },
      { path: "*", element: <Navigate to="/" replace /> },
    ],
  },
]);
