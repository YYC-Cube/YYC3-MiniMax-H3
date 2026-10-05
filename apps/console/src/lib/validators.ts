// src/lib/validators.ts — 前端 API/SSE 运行时校验（zod，优先级②类型安全）
// 契约真源：@yyc3/manifest-schema（服务端直读）+ 本文件（客户端消费端）
import { z } from "zod";
import { batchesPayloadSchema, manifestSchema } from "@yyc3/manifest-schema";

export const logLineSchema = z.object({ ts: z.number(), text: z.string() });
export type LogLine = z.infer<typeof logLineSchema>;

export const runStatusSchema = z.object({
  state: z.enum(["idle", "running", "completed", "failed"]),
  batch: z.string().nullable(),
  startedAt: z.number().nullable(),
  endedAt: z.number().nullable(),
  exitCode: z.number().nullable(),
  runId: z.number().optional(),
});
export type RunStatus = z.infer<typeof runStatusSchema>;

export const fileChangeSchema = z.object({
  path: z.string(),
  kind: z.enum(["manifest", "report", "batches"]),
  ts: z.number(),
});
export type FileChange = z.infer<typeof fileChangeSchema>;

/** 网关任务视图（passthrough：网关扩展字段不拒收） */
export const taskViewSchema = z
  .object({
    id: z.string(),
    status: z.enum(["queued", "running", "succeeded", "failed"]),
    quality: z.string().nullable().optional(),
    created_at: z.number().nullable().optional(),
    updated_at: z.number().nullable().optional(),
    attempts: z.number().optional(),
    error: z.string().nullable().optional(),
    result_url: z.string().optional(),
    archive_path: z.string().nullable().optional(),
    duration_seconds: z.number().nullable().optional(),
  })
  .passthrough();
export type TaskView = z.infer<typeof taskViewSchema>;

export const taskListSchema = z.object({ tasks: z.array(taskViewSchema) }).passthrough();

export const createTaskSchema = z
  .object({ id: z.string(), queue_position: z.number().optional() })
  .passthrough();
export type CreateTaskResult = z.infer<typeof createTaskSchema>;

export const dashboardSchema = z.object({
  manifests: z.array(manifestSchema),
  payload: batchesPayloadSchema.nullable(),
  errors: z.array(z.string()),
});
export type DashboardData = z.infer<typeof dashboardSchema>;

export const scoreRowsSchema = z.object({
  batch: z.string(),
  rows: z.array(
    z.object({
      ref: z.string(),
      seed: z.number(),
      status: z.string(),
      video: z.string(),
      lipsync: z.string(),
      score: z.string(),
      tags: z.string(),
    })
  ),
});
export type ScoreRows = z.infer<typeof scoreRowsSchema>;

/** 分镜确认闸门（P1-1，agent 网关 /api/stages/storyboard） */
export const storyboardStatusSchema = z.object({
  batch: z.string().nullable(),
  status: z.string(), // 六态：pending/running/passed/rework/blocked/waiting_feedback
  candidates: z.array(z.string()),
  selected: z.string().nullable().optional(),
});
export type StoryboardStatus = z.infer<typeof storyboardStatusSchema>;

/** 解析并校验 JSON 字符串；失败返回 null（SSE 坏数据降级不崩 UI） */
export function safeParseJson<T>(raw: string, schema: z.ZodType<T>): T | null {
  try {
    const parsed = JSON.parse(raw);
    const result = schema.safeParse(parsed);
    return result.success ? result.data : null;
  } catch {
    return null;
  }
}
