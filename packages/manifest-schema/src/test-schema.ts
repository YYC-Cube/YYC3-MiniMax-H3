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
import { fileURLToPath } from "node:url";
import { assetsManifestSchema, manifestSchema, recordSchema } from "./index";

const repoRoot = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..", "..", "..");
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

// P0-1/P0-2/P1-3 契约扩展冒烟（docs/18，2026-10-05）：record 演进字段 + reason + assets 清单 fixture
{
  const rec = recordSchema.safeParse({
    ref_img: "characters/person-a.png", seed: 7, status: "SUCCESS",
    video_mode: "ref2va", asset_ref: "characters/person-a.png", pacing: "grid07/climax",
  });
  console.log(`fixture(evolution-record): ${rec.success ? "✅ video_mode/asset_ref/pacing OK" : "❌ " + JSON.stringify(rec.error.issues.slice(0, 2))}`);
  if (!rec.success) process.exitCode = 1;

  const bad = recordSchema.safeParse({ ref_img: "x.png", seed: 1, status: "SUCCESS", video_mode: "t2v" });
  if (bad.success) {
    console.log("fixture(evolution-record): ❌ 非法 video_mode 未被拒绝");
    process.exitCode = 1;
  } else {
    console.log("fixture(evolution-record): ✅ 非法 video_mode 正确拒绝");
  }

  // P1-3 失败模式枚举
  const fail = recordSchema.safeParse({ ref_img: "x.png", seed: 1, status: "FAILED", reason: "sigterm" });
  const failBad = recordSchema.safeParse({ ref_img: "x.png", seed: 1, status: "FAILED", reason: "crash_x" });
  if (fail.success && !failBad.success) {
    console.log("fixture(evolution-record): ✅ reason 枚举通过/非法拒绝");
  } else {
    console.log("fixture(evolution-record): ❌ reason 枚举校验异常");
    process.exitCode = 1;
  }

  const assets = assetsManifestSchema.safeParse({
    schema_version: 1, generated_at: "2026-10-05T00:00:00",
    assets: [
      { id: "person-a", kind: "characters", name: "Person A",
        files: ["characters/person_a.png"], tags: ["主角"] },
      { id: "rain-street", kind: "scenes", name: "雨街",
        files: ["scenes/rain_1.png", "scenes/rain_2.png"], tags: [] },
    ],
  });
  console.log(`fixture(assets-manifest): ${assets.success ? "✅ 清单契约 OK" : "❌ " + JSON.stringify(assets.error.issues.slice(0, 2))}`);
  if (!assets.success) process.exitCode = 1;
}
