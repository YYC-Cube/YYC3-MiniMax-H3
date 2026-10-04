// src/main.tsx — 应用入口（会话令牌先行 + RouterProvider）
import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import { RouterProvider } from "react-router-dom";
import { router } from "./router";
import { initSession } from "./lib/api";
import "./styles/globals.css";

// 先换取短时会话令牌（失败静默——回环/无令牌部署由服务端直接放行）
void initSession();

createRoot(document.getElementById("root")!).render(
  <StrictMode>
    <RouterProvider router={router} />
  </StrictMode>
);
