/**
 * @file packages/manifest-schema/src/index.ts
 * @author YanYuCloudCube Team <admin@0379.email>
 * @version v1.0.0
 * @created 2026-09-03
 * @updated 2026-09-03
 *
 * manifest.json zod schema — 双端契约唯一真源
 * 写端：scripts/analyze_report.py（Python）；读端：apps/console（Next.js RSC）
 * 修改本文件前必须同步 Python 写端，或以 JSON Schema 双端生成（路线C）。
 */
import { z } from "zod";

/** 单条生成记录（SUCCESS/SKIPPED/FAILED 等状态） */
export const recordSchema = z.object({
  ref_img: z.string(),
  seed: z.number().int(),
  status: z.string(), // SUCCESS | SKIPPED | FAILED | ...
  video_path: z.string().optional(),
  gen_seconds: z.number().optional(),
  peak_rss_gb: z.number().optional(),
  lipsync: z
    .object({
      score_norm: z.number().optional(),
      av_offset: z.number().optional(),
      confidence: z.number().optional(),
    })
    .optional(),
  human: z
    .object({
      score: z.number().nullable().optional(), // null = 待人工精评
      tags: z.string().nullable().optional(),
      notes: z.string().nullable().optional(),
    })
    .optional(),
});
export type Record = z.infer<typeof recordSchema>;

/** 单批次 manifest（output_batchXX/manifest.json） */
export const manifestSchema = z.object({
  batch: z.string(),
  started_at: z.string(),
  ended_at: z.string().nullable().optional(),
  model: z.object({
    pipeline: z.string().default("ref2va"),
    variant: z.string().default("nf4"),
  }),
  params: z.record(z.string(), z.unknown()).default({}),
  records: z.array(recordSchema),
});
export type Manifest = z.infer<typeof manifestSchema>;

/** 面板聚合数据（dashboard/data/batches.json，export_dashboard_data.py 写出） */
export const batchesPayloadSchema = z.object({
  schema_version: z.number().int(),
  generated_at: z.string(),
  score_scale: z.string(),
  batches: z.array(
    z.object({
      id: z.string(),
      time: z.string(),
      ended: z.string().nullable().optional(),
      model: z.string(),
      pipeline: z.string(),
      refImages: z.number().int(),
      seeds: z.number().int(),
      success: z.number().int(),
      failed: z.number().int(),
      skipped: z.number().int(),
      avgScore: z.number(),
      maxScore: z.number(),
      status: z.string(),
      videos: z.array(
        z.object({
          name: z.string(),
          ref: z.string(),
          seed: z.number().int(),
          score: z.number(),
          source: z.string(),
          tags: z.array(z.string()),
          video_path: z.string().optional(),
          gen_seconds: z.number().optional(),
          peak_rss_gb: z.number().optional(),
          av_offset: z.number().optional(),
        })
      ),
      defects: z.record(z.string(), z.number()),
      params: z.record(z.string(), z.unknown()),
      durationMin: z.number().nullable().optional(),
    })
  ),
  top10: z.array(
    z.object({
      rank: z.number().int(),
      batch: z.string(),
      img: z.string(),
      seed: z.number().int(),
      score: z.number(),
      tags: z.array(z.string()),
    })
  ),
});
export type BatchesPayload = z.infer<typeof batchesPayloadSchema>;
