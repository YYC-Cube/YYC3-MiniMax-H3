/**
 * @file packages/manifest-schema/src/assets.ts
 * @author YanYuCloudCube Team <admin@0379.email>
 * @version v1.0.0
 * @created 2026-10-05
 * @updated 2026-10-05
 *
 * Ref 资产库清单契约（docs/18 §四 P0-2，对齐 OnlyShot 工业级 Ref 库规范）
 * 目录：ref_images/{characters,scenes,props}/（.gitignore 引擎区，本清单不入库；
 *       清单文件 ref_images/assets.json 由 organize_ref_assets.py 生成/维护）
 * 消费端：分镜确认流（P1-2，console 选图写 asset_ref）/ 生成脚本关联 Ref
 */
import { z } from "zod";

export const ASSET_KINDS = ["characters", "scenes", "props"] as const;
export type AssetKind = (typeof ASSET_KINDS)[number];

/** 单个资产条目（如一位角色的全部定妆/动作/表情图集） */
export const assetItemSchema = z.object({
  id: z.string(), // 唯一标识（slug，如 person-a）
  kind: z.enum(ASSET_KINDS),
  name: z.string(), // 显示名（如 "Person A · 古风女主"）
  files: z.array(z.string()).min(1), // 相对 ref_images/ 的文件路径（多图=图集：定妆/动作/表情/多角度）
  tags: z.array(z.string()).default([]), // 检索标签（造型/情绪/角度…，对齐 BigBanana 衣橱思路）
  notes: z.string().optional(),
  created_at: z.string().optional(), // ISO8601
  updated_at: z.string().optional(),
});
export type AssetItem = z.infer<typeof assetItemSchema>;

/** 资产清单（ref_images/assets.json） */
export const assetsManifestSchema = z.object({
  schema_version: z.literal(1),
  generated_at: z.string(),
  assets: z.array(assetItemSchema),
});
export type AssetsManifest = z.infer<typeof assetsManifestSchema>;
