// scripts/dev.mjs — 开发双进程编排（API 3031 + Vite 3030 代理 /api），Ctrl-C 级联退出
import { spawn } from "node:child_process";
import path from "node:path";
import { fileURLToPath } from "node:url";

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");
const bin = (name) => path.join(root, "node_modules", ".bin", name);
const children = [];

const start = (cmd, args, label) => {
  const child = spawn(cmd, args, { stdio: "inherit", cwd: root });
  child.on("exit", (code) => {
    if (code !== 0 && !process.exitCode) console.log(`[dev] ${label} 退出（code=${code}）`);
  });
  children.push(child);
  return child;
};

start(bin("tsx"), ["watch", "server/index.ts"], "api");
start(bin("vite"), [], "vite");

const shutdown = () => {
  for (const c of children) c.kill("SIGTERM");
  setTimeout(() => process.exit(0), 300);
};
process.on("SIGINT", shutdown);
process.on("SIGTERM", shutdown);
