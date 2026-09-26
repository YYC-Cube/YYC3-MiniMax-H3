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
export const recordSchema = z
  .object({
    ref_img: z.string(),
    seed: z.number().int(),
    status: z.string(), // SUCCESS | SKIPPED | FAILED | ...
    video_path: z.string().optional(),
    gen_seconds: z.number().optional(),
    peak_rss_gb: z.number().optional(),
    time: z.string().optional(), // 写端扩展：完成时刻 HH:MM:SS
    mps_alloc_gb: z.number().optional(), // 写端扩展：MPS 统计
    lipsync: z
      .object({
        score_norm: z.number().nullable().optional(), // heuristic 后端写 null（快照实证 batch92）
        av_offset: z.number().optional(),
        confidence: z.number().nullable().optional(), // 同上：不可计算时为 null 而非缺省
        backend: z.string().optional(), // syncnet | heuristic
        scored_at: z.string().optional(),
      })
      .optional(),
    human: z
      .object({
        score: z.number().nullable().optional(), // null = 待人工精评
        tags: z.string().nullable().optional(),
        notes: z.string().nullable().optional(),
      })
      .optional(),
  })
  .passthrough(); // 写端可携带扩展字段，读端不强拒（契约只锁定已知关键字段）
export type Record = z.infer<typeof recordSchema>;

/** 单批次 manifest（output_batchXX/manifest.json） */
export const manifestSchema = z
  .object({
    batch: z.string(),
    started_at: z.string(),
    ended_at: z.string().nullable().optional(),
    model: z.object({
      pipeline: z.string().default("ref2va"),
      variant: z.string().default("nf4"),
    }),
    params: z.record(z.string(), z.unknown()).default({}),
    records: z.array(recordSchema),
  })
  .passthrough(); // schema_version 等写端扩展字段放行
export type Manifest = z.infer<typeof manifestSchema>;

// batches.json 面板聚合契约：唯一真源已迁至 ./batches（2026-09-26 去重，原内联定义移除；
// 直接导出对 export * 具名遮蔽会静默生效，故不再保留内联副本）
export * from "./batches";
