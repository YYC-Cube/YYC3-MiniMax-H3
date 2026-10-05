// src/router.tsx — 应用路由（react-router v7；仅首屏 Dashboard 预载，其余页面全部懒加载）
// 拆分策略：首屏 eager 保 TTFB；Pipeline/Tasks/BatchDetail/Assistant 按需 chunk
import { lazy, Suspense } from "react";
import { createBrowserRouter, Navigate } from "react-router-dom";
import App from "@/App";
import DashboardPage from "@/pages/DashboardPage";
import { Loader2 } from "lucide-react";

const PipelinePage = lazy(() => import("@/pages/PipelinePage"));
const TasksPage = lazy(() => import("@/pages/TasksPage"));
const BatchDetailPage = lazy(() => import("@/pages/BatchDetailPage"));
const AssistantPage = lazy(() => import("@/pages/AssistantPage"));
const StoryboardPage = lazy(() => import("@/pages/StoryboardPage"));

function PageFallback() {
  return (
    <div className="flex items-center gap-2 py-16 text-muted-foreground" role="status" aria-live="polite">
      <Loader2 className="animate-spin" />
      页面加载中…
    </div>
  );
}

function lazyPage(Page: React.LazyExoticComponent<React.ComponentType>) {
  return (
    <Suspense fallback={<PageFallback />}>
      <Page />
    </Suspense>
  );
}

export const router = createBrowserRouter([
  {
    element: <App />,
    children: [
      { path: "/", element: <DashboardPage /> },
      { path: "/pipeline", element: lazyPage(PipelinePage) },
      { path: "/tasks", element: lazyPage(TasksPage) },
      { path: "/batches/:id", element: lazyPage(BatchDetailPage) },
      { path: "/assistant", element: lazyPage(AssistantPage) },
      { path: "/storyboard", element: lazyPage(StoryboardPage) },
      { path: "*", element: <Navigate to="/" replace /> },
    ],
  },
]);
