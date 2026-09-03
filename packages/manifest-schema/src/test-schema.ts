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
  console.log("⚠ 未找到 output_batch*/manifest.json");
  process.exitCode = 1;
}
