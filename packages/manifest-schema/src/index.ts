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
// reconciledSchema 定义在 ./batches（index 末尾 export * batches，反向单向引用无循环）
import { reconciledSchema } from "./batches.js";

/** 单条生成记录（SUCCESS/SKIPPED/FAILED 等状态） */
export const recordSchema = z
  .object({
    ref_img: z.string(),
    seed: z.number().int(),
    status: z.string(), // SUCCESS | SKIPPED | FAILED | ...
    video_path: z.string().optional(),
    gen_seconds: z.number().nullable().optional(), // FAILED/中断记录写端初始 null（同 lipsync 先例）
    peak_rss_gb: z.number().nullable().optional(),
    time: z.string().optional(), // 写端扩展：完成时刻 HH:MM:SS
    mps_alloc_gb: z.number().nullable().optional(), // 写端扩展：MPS 统计
    lipsync: z
      .object({
        score_norm: z.number().nullable().optional(), // heuristic 后端写 null（快照实证 batch92）
        av_offset: z.number().optional(),
        confidence: z.number().nullable().optional(), // 同上：不可计算时为 null 而非缺省
        backend: z.string().optional(), // syncnet | heuristic
        scored_at: z.string().optional(),
      })
      .nullable() // h3_common.add_record 初始写 null，score_lipsync.py 回填后为对象
      .optional(),
    human: z
      .object({
        score: z.number().nullable().optional(), // null = 待人工精评
        tags: z.string().nullable().optional(),
        notes: z.string().nullable().optional(),
      })
      .optional(),
    // ---- P0-1 演进扩展（docs/18 §四，2026-10-05）：全部 optional 向后兼容，旧 manifest 零影响 ----
    // 写端（h3_common.add_record）尚未产出：P1-2 分镜确认流接入时启用；当前由读端/资产工具预填
    video_mode: z
      .enum(["ref2va", "fl2va", "frames"])
      .optional(), // 生成模式路由（OnlyShot 四模对位；frames=首尾帧插值，P2-1 探测后才启用写端）
    asset_ref: z.string().optional(), // Ref 资产库关联路径（ref_images/{characters,scenes,props}/…，见 assets.ts 清单）
    pacing: z.string().optional(), // 节奏元数据（grid 标识/爆点标记等，创作层回传分析用，本仓不实现节奏逻辑）
    // P1-3 失败模式结构化（docs/18，2026-10-05）：FAILED 记录失败原因枚举（OnlyShot 17 式的引擎子集起步）
    reason: z
      .enum([
        "sigterm",          // SIGTERM/SIGINT 优雅终止（窗口截止人工清场/kill）
        "window_timeout",   // 夜间窗口截止（夜间编排判定，预留）
        "oom",              // 显存/内存溢出（预留）
        "model_error",      // 模型推理异常（通用种子级 except）
        "score_backend_missing", // SyncNet 权重缺失降级失败（预留）
        "ref_missing",      // 参考图缺失/越界（预留）
        "unknown",          // 历史记录/未归类（读端兜底）
      ])
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
    reconciled: reconciledSchema.optional(), // 僵尸批次收敛块（见 reconciledSchema 注释）
  })
  .passthrough(); // schema_version 等写端扩展字段放行
export type Manifest = z.infer<typeof manifestSchema>;

// batches.json 面板聚合契约：唯一真源已迁至 ./batches（2026-09-26 去重，原内联定义移除；
// 直接导出对 export * 具名遮蔽会静默生效，故不再保留内联副本）
export * from "./batches.js";

// Ref 资产库清单契约（docs/18 P0-2，2026-10-05）
export * from "./assets.js";
