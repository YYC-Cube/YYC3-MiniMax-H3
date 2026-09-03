/**
 * @file packages/manifest-schema/src/gen-json-schema.ts
 * Contract: single source of truth zod -> JSON Schema for the Python side.
 * Output: packages/manifest-schema/schema/manifest.schema.json (+ batches payload)
 */
import fs from "node:fs";
import path from "node:path";
import { zodToJsonSchema } from "zod-to-json-schema";
import { batchesPayloadSchema, manifestSchema } from "./index";

const outDir = path.join(__dirname, "..", "schema");
fs.mkdirSync(outDir, { recursive: true });

for (const [name, schema] of [
  ["manifest.schema.json", manifestSchema],
  ["batches.schema.json", batchesPayloadSchema],
] as const) {
  // 不指定 target：默认 Draft-07，正确输出 nullable: [type, "null"]
  const json = zodToJsonSchema(schema, { name: name.replace(".schema.json", "") });
  const file = path.join(outDir, name);
  fs.writeFileSync(file, JSON.stringify(json, null, 2) + "\n");
  console.log("generated:", path.relative(process.cwd(), file));
}
