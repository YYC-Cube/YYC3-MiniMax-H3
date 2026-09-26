/**
 * @file packages/manifest-schema/src/batches.ts
 * @author YanYuCloudCube Team <admin@0379.email>
 * @version v1.0.0
 * @created 2026-09-26
 * @updated 2026-09-26
 *
 * dashboard/data/batches.json zod schema — 面板数据源双端契约（P1-C2 归一决策固化）
 * 写端：scripts/pipeline-tools/export_dashboard_data.py（pipeline_auto ⑤' 唯一写端）
 * 读端：可视化面板 / 网关；字段名与写端 build_batch()/payload 构造一一对应
 * 一致性校验：scripts/pipeline-tools/check_contract_sync.py（CI 门禁，字段清单见下方 const）
 */
import { z } from "zod";

/** 契约字段清单（机器可读表面，供 check_contract_sync.py 与 Python 写端比对） */
export const BATCH_ENVELOPE_FIELDS = [
  "schema_version",
  "generated_at",
  "score_scale",
  "batches",
  "top10",
] as const;

export const BATCH_UNIT_FIELDS = [
  "id",
  "time",
  "ended",
  "model",
  "pipeline",
  "refImages",
  "seeds",
  "success",
  "failed",
  "skipped",
  "avgScore",
  "maxScore",
  "status",
  "videos",
  "defects",
  "params",
  "durationMin",
] as const;

export const batchVideoSchema = z.object({
  name: z.string(),
  ref: z.string(),
  seed: z.number().nullable().optional(),
  score: z.number(),
  source: z.string(),
  tags: z.array(z.string()),
  video_path: z.string(),
  gen_seconds: z.number().nullable().optional(),
  peak_rss_gb: z.number().nullable().optional(),
  av_offset: z.number().nullable().optional(),
});

export const batchUnitSchema = z.object({
  id: z.string(),
  time: z.string(), // started_at（"YYYY-MM-DD HH:MM"）
  ended: z.string().nullable(), // ended_at 或 None（running 批次）
  model: z.string(), // 变体大写（NF4/FP8/…）
  pipeline: z.string(), // 默认 ref2va
  refImages: z.number().int(),
  seeds: z.number().int(),
  success: z.number().int(),
  failed: z.number().int(),
  skipped: z.number().int(),
  avgScore: z.number(), // 0-10（score_scale 见 envelope）
  maxScore: z.number(),
  status: z.string(), // completed | running
  videos: z.array(batchVideoSchema),
  defects: z.record(z.number()), // 缺陷标签 → 次数（降序）
  params: z.record(z.number()).optional(), // height/width/num_frames/num_inference_steps/fps 子集
  durationMin: z.number().nullable(),
});

export const top10ItemSchema = z.object({
  // 形状取自 export_dashboard_data.py top10 构造（快照实证：rank/batch/img/seed/score/tags）
  rank: z.number().int(),
  batch: z.string(),
  img: z.string(),
  seed: z.number().int(),
  score: z.number(),
  tags: z.array(z.string()),
});

export const batchesPayloadSchema = z.object({
  schema_version: z.literal(1),
  generated_at: z.string(), // ISO8601 seconds
  score_scale: z.string(),
  batches: z.array(batchUnitSchema),
  top10: z.array(top10ItemSchema),
});

export type BatchVideo = z.infer<typeof batchVideoSchema>;
export type BatchUnit = z.infer<typeof batchUnitSchema>;
export type Top10Item = z.infer<typeof top10ItemSchema>;
export type BatchesPayload = z.infer<typeof batchesPayloadSchema>;
