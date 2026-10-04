// server/lib/pipeline-manager.ts — 单例流水线引擎（自 Next 进程内单例平移）
// spawn 白名单 + 环形日志 + 发布订阅 + 文件变更总线（manifest/report/batches → SSE 推送）
import { spawn, type ChildProcess } from "node:child_process";
import fs from "node:fs";
import path from "node:path";

export type RunState = "idle" | "running" | "completed" | "failed";

export interface LogLine {
  ts: number;
  text: string;
}

export interface FileChange {
  path: string; // 相对仓库根
  kind: "manifest" | "report" | "batches";
  ts: number;
}

export interface RunStatus {
  state: RunState;
  batch: string | null;
  startedAt: number | null;
  endedAt: number | null;
  exitCode: number | null;
}

const RING_MAX = 2000;
const REPLAY_MAX = 300;

class PipelineManager {
  private proc: ChildProcess | null = null;
  private ring: LogLine[] = [];
  private subscribers = new Set<(line: LogLine) => void>();
  private status: RunStatus = {
    state: "idle",
    batch: null,
    startedAt: null,
    endedAt: null,
    exitCode: null,
  };
  private runId = 0;
  readonly logDir: string;

  // ---- 文件变更总线：manifest/report/batches 变化 → SSE `file` 事件 → 仪表盘自动刷新 ----
  private watcher: fs.FSWatcher | null = null;
  private fileSubscribers = new Set<(change: FileChange) => void>();
  private pendingChanges = new Map<string, FileChange>();
  private debounceTimer: ReturnType<typeof setTimeout> | null = null;

  constructor() {
    this.logDir = path.resolve(process.cwd(), "..", "..", "output_logs");
    fs.mkdirSync(this.logDir, { recursive: true });
    this.startWatcher();
  }

  // 递归监听仓库根目标文件；macOS/Windows 原生递归，Linux 降级为仅顶层（本仓库批次目录在顶层，够用）
  private startWatcher() {
    const repoRoot = path.resolve(process.cwd(), "..", "..");
    try {
      this.watcher = fs.watch(
        repoRoot,
        { recursive: true },
        (_event, filename) => {
          if (!filename) return;
          const p = String(filename);
          const kind = p.endsWith("manifest.json")
            ? "manifest"
            : /report_batch\d+\.md$/.test(p)
              ? "report"
              : p.endsWith("batches.json")
                ? "batches"
                : null;
          if (!kind) return;
          if (/node_modules|\.next|dist|output_logs/.test(p)) return;
          this.enqueueChange({ path: p, kind, ts: Date.now() });
        }
      );
      this.watcher.on("error", () => {
        // 监听失败不致命：页面仍有手动刷新兜底
        this.watcher = null;
      });
    } catch {
      this.watcher = null;
    }
  }

  /** 500ms 去抖合并（批量写 manifest 时避免风暴） */
  private enqueueChange(change: FileChange) {
    this.pendingChanges.set(change.path, change);
    if (this.debounceTimer) return;
    this.debounceTimer = setTimeout(() => {
      this.debounceTimer = null;
      for (const c of this.pendingChanges.values()) {
        for (const fn of this.fileSubscribers) fn(c);
      }
      this.pendingChanges.clear();
    }, 500);
  }

  subscribeFiles(fn: (change: FileChange) => void): () => void {
    this.fileSubscribers.add(fn);
    return () => this.fileSubscribers.delete(fn);
  }

  getStatus(): RunStatus & { runId: number } {
    return { ...this.status, runId: this.runId };
  }

  /** 回填最近 REPLAY_MAX 行 + 当前状态 */
  replay(): { status: RunStatus & { runId: number }; logs: LogLine[] } {
    return { status: this.getStatus(), logs: this.ring.slice(-REPLAY_MAX) };
  }

  isRunning(): boolean {
    return this.status.state === "running" && this.proc !== null;
  }

  /**
   * 触发流水线。spawn 白名单：只允许本仓库 scripts/pipeline-tools/pipeline_auto.py。
   * batch: 两位批次号（^\d{2}$）；dryRun: 演练模式（不实际执行）。
   */
  start(
    batch: string | null,
    dryRun: boolean
  ): { ok: boolean; error?: string; batch?: string } {
    if (this.isRunning())
      return {
        ok: false,
        error: "已有流水线在运行（单飞锁）",
        batch: this.status.batch ?? undefined,
      };

    const repoRoot = path.resolve(process.cwd(), "..", "..");
    const script = path.join(repoRoot, "scripts", "pipeline-tools", "pipeline_auto.py");
    if (!fs.existsSync(script))
      return { ok: false, error: `白名单脚本不存在: ${script}` };

    if (batch != null && !/^\d{2}$/.test(batch))
      return { ok: false, error: "批次号须为两位数字（如 03）" };

    const args = [script];
    if (batch) args.push("--batch", batch);
    args.push("--auto"); // 非交互必加：input() 无 stdin 会抛 EOFError
    if (dryRun) args.push("--dry-run");

    this.runId += 1;
    this.ring = [];
    this.status = {
      state: "running",
      batch: batch ?? null,
      startedAt: Date.now(),
      endedAt: null,
      exitCode: null,
    };

    const logFile = path.join(this.logDir, `run_${String(this.runId).padStart(4, "0")}_${Date.now()}.log`);
    const logStream = fs.createWriteStream(logFile, { flags: "a" });
    this.log(`🚀 启动流水线 run#${this.runId}（${dryRun ? "DRY-RUN" : "真实执行"}）→ 日志 ${path.basename(logFile)}`);

    // PYTHONUNBUFFERED=1：Python 子进程 stdout 无缓冲，SSE 才能逐行实时
    this.proc = spawn(process.env.PIPELINE_PYTHON ?? "python3", args, {
      cwd: repoRoot, // pipeline_auto 以根目录 CWD glob report_batch*（批次号递增依赖）
      env: { ...process.env, PYTHONUNBUFFERED: "1" },
    });

    const onLine = (chunk: Buffer) => {
      for (const raw of chunk.toString("utf-8").split(/\r?\n/)) {
        if (!raw) continue;
        const line = { ts: Date.now(), text: raw };
        this.ring.push(line);
        if (this.ring.length > RING_MAX) this.ring.splice(0, this.ring.length - RING_MAX);
        logStream.write(raw + "\n");
        for (const fn of this.subscribers) fn(line);
      }
    };
    this.proc.stdout?.on("data", onLine);
    this.proc.stderr?.on("data", onLine);

    this.proc.on("close", (code) => {
      this.status = {
        ...this.status,
        state: code === 0 ? "completed" : "failed",
        endedAt: Date.now(),
        exitCode: code,
      };
      this.log(code === 0 ? "🏁 流水线执行成功" : `❌ 流水线退出码 ${code}`);
      this.proc = null;
      logStream.end();
    });
    this.proc.on("error", (err) => {
      this.log(`❌ spawn 失败: ${err.message}`);
      this.status = { ...this.status, state: "failed", endedAt: Date.now() };
      this.proc = null;
      logStream.end();
    });

    return { ok: true, batch: batch ?? "auto" };
  }

  /** SSE 日志订阅；返回退订函数 */
  subscribe(fn: (line: LogLine) => void): () => void {
    this.subscribers.add(fn);
    return () => this.subscribers.delete(fn);
  }

  private log(text: string) {
    const line = { ts: Date.now(), text };
    this.ring.push(line);
    if (this.ring.length > RING_MAX) this.ring.splice(0, this.ring.length - RING_MAX);
    for (const fn of this.subscribers) fn(line);
  }
}

// tsx watch 热重启会重复实例化——挂到 globalThis 保证单例（进程级）
const g = globalThis as unknown as { __pipelineManager?: PipelineManager };
export const pipelineManager: PipelineManager = (g.__pipelineManager ??= new PipelineManager());
