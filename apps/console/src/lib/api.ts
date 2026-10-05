// src/lib/api.ts — 类型化 API 客户端 + 会话令牌注入
// 令牌只存内存（不落 URL/localStorage），满足「URL 传密钥永禁」铁律
import { z } from "zod";
import {
  createTaskSchema,
  dashboardSchema,
  runStatusSchema,
  scoreRowsSchema,
  storyboardStatusSchema,
  taskListSchema,
  type CreateTaskResult,
  type DashboardData,
  type RunStatus,
  type ScoreRows,
  type StoryboardStatus,
  type TaskView,
} from "./validators";

let sessionToken: string | null = null;

/** 启动时换取短时会话令牌；失败静默（回环/无令牌部署直接放行） */
export async function initSession(): Promise<void> {
  try {
    const res = await fetch("/api/session", { cache: "no-store" });
    if (res.ok) {
      const data: unknown = await res.json();
      if (typeof data === "object" && data && typeof (data as { token?: unknown }).token === "string") {
        sessionToken = (data as { token: string }).token;
      }
    }
  } catch {
    /* noop */
  }
}

function authHeaders(): Record<string, string> {
  return sessionToken
    ? { "x-claim-token": sessionToken, authorization: `Bearer ${sessionToken}` }
    : {};
}

export async function apiFetch(input: string, init?: RequestInit): Promise<Response> {
  return fetch(input, {
    ...init,
    headers: { ...authHeaders(), ...(init?.headers ?? {}) },
    cache: init?.cache ?? "no-store",
  });
}

/** 校验并返回 schema 的输出类型（默认值/转换后形态） */
async function jsonOrThrow<S extends z.ZodTypeAny>(schema: S, res: Response): Promise<z.output<S>> {
  const data: unknown = await res.json().catch(() => null);
  if (!res.ok) throw new Error((data as { error?: string } | null)?.error ?? `HTTP ${res.status}`);
  const parsed = schema.safeParse(data);
  if (!parsed.success) {
    throw new Error(`响应契约校验失败: ${parsed.error.issues[0]?.message ?? ""}`);
  }
  return parsed.data;
}

export async function getDashboard(): Promise<DashboardData> {
  const res = await apiFetch("/api/dashboard");
  return jsonOrThrow(dashboardSchema, res);
}

export async function getPipelineStatus(): Promise<RunStatus> {
  const res = await apiFetch("/api/pipeline");
  return jsonOrThrow(runStatusSchema, res);
}

export async function triggerPipeline(
  batch: string | null,
  dryRun: boolean
): Promise<{ started: boolean; batch?: string; error?: string }> {
  const res = await apiFetch("/api/pipeline/run", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ batch, dryRun }),
  });
  const data: unknown = await res.json().catch(() => null);
  if (!res.ok) throw new Error((data as { error?: string } | null)?.error ?? `HTTP ${res.status}`);
  return data as { started: boolean; batch?: string };
}

export async function getTasks(): Promise<TaskView[]> {
  const res = await apiFetch("/api/tasks");
  const data = await jsonOrThrow(taskListSchema, res);
  return data.tasks ?? [];
}

export interface TaskSubmitInput {
  prompt?: string;
  quality: "preview" | "full";
  seed?: number;
  refImageB64?: string;
  refImageName?: string;
}

export async function createTask(input: TaskSubmitInput): Promise<CreateTaskResult> {
  const res = await apiFetch("/api/tasks", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(input),
  });
  return jsonOrThrow(createTaskSchema, res);
}

export interface ScoreInput {
  batch: string;
  ref: string;
  seed: number;
  score: number;
  tags?: string;
}

export async function saveScore(input: ScoreInput): Promise<void> {
  const res = await apiFetch("/api/score", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(input),
  });
  const data: unknown = await res.json().catch(() => null);
  if (!res.ok) throw new Error((data as { error?: string } | null)?.error ?? `HTTP ${res.status}`);
}

export async function getScoreRows(batch: string): Promise<ScoreRows> {
  const res = await apiFetch(`/api/score?batch=${encodeURIComponent(batch)}`);
  return jsonOrThrow(scoreRowsSchema, res);
}

// ---- 分镜确认闸门（P1-1/P1-2） ----

export async function getStoryboard(): Promise<StoryboardStatus> {
  const res = await apiFetch("/api/storyboard");
  return jsonOrThrow(storyboardStatusSchema, res);
}

export async function submitStoryboard(batch: string, candidates: string[]): Promise<void> {
  const res = await apiFetch("/api/storyboard/submit", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ batch, candidates }),
  });
  if (!res.ok) {
    const data: unknown = await res.json().catch(() => null);
    throw new Error((data as { error?: string } | null)?.error ?? `HTTP ${res.status}`);
  }
}

export interface ConfirmInput {
  selected: string;
  asset_ref?: string;
  quality?: "preview" | "full";
  dry_run?: boolean;
}

export async function confirmStoryboard(input: ConfirmInput): Promise<{ verdict?: string }> {
  const res = await apiFetch("/api/storyboard/confirm", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(input),
  });
  const data: unknown = await res.json().catch(() => null);
  if (!res.ok) throw new Error((data as { error?: string } | null)?.error ?? `HTTP ${res.status}`);
  return (data as { verdict?: string }) ?? {};
}
