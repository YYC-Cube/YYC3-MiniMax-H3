/**
 * @file packages/manifest-schema/src/test-schema.ts
 * @author YanYuCloudCube Team <admin@0379.email>
 * @version v1.0.0
 * @created 2026-09-03
 * @updated 2026-09-03
 *
 * 契约冒烟测试：用仓库真实 manifest.json 校验 zod schema（双端不错位的门禁）
 */
import fs from "node:fs";
import path from "node:path";
import { manifestSchema } from "./index";

const repoRoot = path.resolve(__dirname, "..", "..", "..");
let checked = 0;
for (const d of fs.readdirSync(repoRoot).filter((d) => /^output_batch/.test(d)).sort()) {
  const file = path.join(repoRoot, d, "manifest.json");
  if (!fs.existsSync(file)) continue;
  const parsed = manifestSchema.safeParse(JSON.parse(fs.readFileSync(file, "utf-8")));
  console.log(`${d}: ${parsed.success ? "✅ schema OK" : "❌ " + JSON.stringify(parsed.error.issues.slice(0, 2))}`);
  if (!parsed.success) process.exitCode = 1;
  checked++;
}
if (!checked) {
  // CI 环境无 output_batch*/ 生成数据（不入库）：回退内置 fixture 保证门禁双端有效
  console.log("⚠ 未找到 output_batch*/manifest.json，回退内置 fixture 校验");
  const fixture = {
    batch: "batch99",
    started_at: "2026-09-03 00:00:00",
    ended_at: null,
    model: { pipeline: "ref2va", variant: "nf4" },
    params: {},
    records: [
      {
        ref_img: "refs/demo.png",
        seed: 42,
        status: "SUCCESS",
        video_path: "output_batch99/demo.mp4",
        gen_seconds: 12.5,
        peak_rss_gb: 32.8,
        lipsync: { score_norm: 0.87, backend: "syncnet", scored_at: "2026-09-03 00:01:00" },
        human: { score: null, tags: null, notes: null },
        extra_future_field: true, // passthrough 放行写端扩展
      },
    ],
    schema_version: 1,
  };
  const parsed = manifestSchema.safeParse(fixture);
  console.log(`fixture: ${parsed.success ? "✅ schema OK" : "❌ " + JSON.stringify(parsed.error.issues.slice(0, 2))}`);
  if (!parsed.success) process.exitCode = 1;
}
