// src/App.tsx — 应用布局（顶栏 + 路由出口）
import { Outlet } from "react-router-dom";
import { AppHeader } from "@/components/layout/AppHeader";
import { Toaster } from "@/components/ui/toaster";

export default function App() {
  return (
    <div className="flex min-h-screen flex-col">
      <AppHeader />
      <main className="mx-auto w-full max-w-[1440px] flex-1 p-6">
        <Outlet />
      </main>
      <footer className="border-t border-border py-3 text-center text-xs text-muted-foreground">
        YYC³ MiniMax-H3 · React 19 + Vite 6 + Tailwind 4 + shadcn/ui + Zustand + Vercel AI SDK
      </footer>
      <Toaster />
    </div>
  );
}
