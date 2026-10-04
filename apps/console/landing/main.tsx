// landing/main.tsx — 落地页入口（GitHub Pages 快照，h3.yyc3.top）
import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import App from "../src/landing/App";
import "../src/styles/globals.css";

createRoot(document.getElementById("root")!).render(
  <StrictMode>
    <App />
  </StrictMode>
);
