// server/routes/score.ts — /api/score：人工精评写回（report_batchXX.md）+ 读回表单初始值
// 写文件端点与 /api/pipeline/run 同策略鉴权（写操作面必鉴权）
import { Hono } from "hono";
import { execFile } from "node:child_process";
import fs from "node:fs";
import path from "node:path";
import { pipelineManager } from "../lib/pipeline-manager.js";
import { authorizePipeline } from "../lib/api-auth.js";

export const scoreRoutes = new Hono();

const REPO_ROOT = path.resolve(process.cwd(), "..", "..");

interface ScoreBody {
  batch: string;
  ref: string;
  seed: number;
  score: number;
  tags?: string;
}

function reportPath(batch: string) {
  return path.join(REPO_ROOT, `report_batch${batch}.md`);
}

/** 校验批次存在且行定位唯一 */
function findRowIndex(lines: string[], ref: string, seed: number): number {
  for (let i = 0; i < lines.length; i++) {
    const line = lines[i];
    if (!line.startsWith("|") || line.includes("---")) continue;
    const cells = line.split("|").map((x) => x.trim());
    // cells: ['', 参考图, Seed, 状态, 视频路径, 时间, 口型分, 评分, 缺陷标签, '']
    if (cells.length < 9) continue;
    if (cells[1] === ref && cells[2] === String(seed)) return i;
  }
  return -1;
}

scoreRoutes.post("/", async (c) => {
  if (!authorizePipeline(c)) return c.json({ error: "unauthorized" }, 401);
  let body: ScoreBody;
  try {
    body = await c.req.json();
  } catch {
    return c.json({ error: "invalid json" }, 400);
  }

  const { batch, ref, seed, score, tags = "" } = body ?? {};
  if (!/^\d{2}$/.test(batch ?? "")) return c.json({ error: "batch 须为两位数字" }, 400);
  if (!ref || typeof seed !== "number") return c.json({ error: "ref/seed 必填" }, 400);
  if (!(score >= 1 && score <= 10)) return c.json({ error: "score 须在 1~10" }, 400);

  const file = reportPath(batch);
  if (!fs.existsSync(file)) return c.json({ error: `report 不存在: ${path.basename(file)}` }, 404);

  const content = fs.readFileSync(file, "utf-8");
  const lines = content.split("\n");
  const idx = findRowIndex(lines, ref, seed);
  if (idx === -1) return c.json({ error: `未找到行: ${ref} / seed ${seed}` }, 404);

  const cells = lines[idx].split("|").map((x) => x.trim());
  cells[7] = String(score); // 评分(1~10)
  cells[8] = tags; // 缺陷标签
  lines[idx] = `| ${cells.slice(1, 9).join(" | ")} |`;
  fs.writeFileSync(file, lines.join("\n"), "utf-8");

  // 写回后刷新数据桥（静默，不阻断精评响应）
  const exportScript = path.join(REPO_ROOT, "scripts", "pipeline-tools", "export_dashboard_data.py");
  if (fs.existsSync(exportScript) && !pipelineManager.isRunning()) {
    execFile(process.env.PIPELINE_PYTHON ?? "python3", [exportScript], { cwd: REPO_ROOT }, () => {});
  }

  return c.json({ ok: true, batch, ref, seed, score, tags });
});

/** GET /api/score?batch=XX — 读取该批次全部行精评状态（表单初始值） */
scoreRoutes.get("/", (c) => {
  if (!authorizePipeline(c)) return c.json({ error: "unauthorized" }, 401);
  const batch = c.req.query("batch") ?? "";
  if (!/^\d{2}$/.test(batch)) return c.json({ error: "batch 须为两位数字" }, 400);
  const file = reportPath(batch);
  if (!fs.existsSync(file)) return c.json({ error: "report 不存在" }, 404);

  const rows: {
    ref: string;
    seed: number;
    status: string;
    video: string;
    lipsync: string;
    score: string;
    tags: string;
  }[] = [];
  for (const line of fs.readFileSync(file, "utf-8").split("\n")) {
    if (!line.startsWith("|") || line.includes("---")) continue;
    const cells = line.split("|").map((x) => x.trim());
    if (cells.length < 9 || cells[1] === "参考图") continue;
    rows.push({
      ref: cells[1],
      seed: Number(cells[2]),
      status: cells[3],
      video: cells[4],
      lipsync: cells[6],
      score: cells[7],
      tags: cells[8],
    });
  }
  return c.json({ batch, rows });
});
