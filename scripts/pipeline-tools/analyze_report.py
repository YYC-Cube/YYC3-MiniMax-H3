# -*- coding: utf-8 -*-
"""
@file analyze_report.py
@author YanYuCloudCube Team <admin@0379.email>
@version v1.1.0
@created 2026-09-02
@updated 2026-09-03
@status stable
@copyright Copyright (c) 2025-2026 YYC3 Team
@license MIT


analyze_report.py — 批量结果分析（双格式兼容版 · Phase 1/2 改造）
来源任务：docs/04-演进规划与闭环优化机制.md

数据源优先级：
1. manifest（推荐）：output_batchXX/manifest.json —— 含客观口型分/耗时/内存峰值
2. legacy（兼容）：report_batchXX.md 表格 —— 旧批次仍可分析

新增能力（vs 旧版）：
- 客观/主观分对照：口型分 vs 人工分的偏差分析（T2.1 联动）
- 耗时统计：平均/最快/最慢 gen_seconds（T3.1 基线数据）
- analysis_result_batchXX.md 输出（批次隔离，供 update_seed_list 消费）
- 智能建议：客观高分但人工低分 → 提示检查音画内容相关性

用法：python analyze_report.py --batch 01
"""
import argparse
import sys
from collections import Counter
from dataclasses import dataclass, field
from pathlib import Path
from typing import List

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "lib"))
from h3_common import Manifest

TOP_N = 5
VALID_TAGS = {"变脸", "手崩", "抖动", "口型错位"}


@dataclass
class VideoRecord:
    ref_img: str
    seed: str
    status: str
    file_path: str
    time_str: str
    score: float | None = None        # 人工分 1~10
    tags: List[str] = field(default_factory=list)
    lipsync_score: float | None = None    # 客观口型分 0~1
    lipsync_backend: str | None = None
    gen_seconds: float | None = None


# ===================== 数据源1：manifest =====================

def load_from_manifest(manifest_path: Path) -> List[VideoRecord]:
    m = Manifest.load(manifest_path)
    rows = list(m.flat_rows())
    return [
        VideoRecord(
            ref_img=r["ref_img"], seed=str(r["seed"]), status=r["status"],
            file_path=r["video_path"], time_str=r["time"],
            score=float(r["score"]) if r["score"] is not None else None,
            tags=[t.strip() for t in r["tags"].split(",") if t.strip() in VALID_TAGS],
            lipsync_score=r["lipsync_score"],
            lipsync_backend=r["lipsync_backend"],
            gen_seconds=r["gen_seconds"],
        ) for r in rows
    ]


# ===================== 数据源2：legacy markdown =====================

def load_from_markdown(md_path: Path) -> List[VideoRecord]:
    import re
    text = md_path.read_text(encoding="utf-8")
    pattern = re.compile(
        r"\|\s*([^|]+?)\s*\|\s*([^|]+?)\s*\|\s*([^|]+?)\s*\|\s*([^|]+?)\s*\|\s*([^|]+?)\s*\|\s*([^|]*?)\s*\|\s*([^|]*?)\s*\|\s*([^|]*?)\s*\|"
    )
    # 识别带口型分的8列新表头 vs 旧7列表头
    lines = text.splitlines()
    header_idx, width = None, 0
    for i, line in enumerate(lines):
        if line.strip().startswith("|") and "参考图" in line and "Seed" in line:
            header_idx = i
            width = len([c for c in line.strip().strip("|").split("|")])
            break
    if header_idx is None:
        return []
    records = []
    for line in lines[header_idx + 1:]:
        line = line.strip()
        if not line.startswith("|") or "----" in line:
            continue
        cells = [c.strip() for c in line.strip().strip("|").split("|")]
        if width == 8 and len(cells) >= 8:
            # 新表头：参考图|Seed|状态|路径|时间|口型分|评分|标签
            ref_img, seed, status, fp, ts, lip_str, score_str, tag_str = cells[:8]
            lip = float(lip_str) if lip_str and lip_str.replace(".", "").isdigit() else None
        elif len(cells) >= 7:
            # 旧表头：参考图|Seed|状态|路径|时间|评分|标签
            ref_img, seed, status, fp, ts, score_str, tag_str = cells[:7]
            lip = None
        else:
            continue
        score = float(score_str) if score_str and score_str.replace(".", "").isdigit() else None
        tags = [t.strip() for t in tag_str.split(",") if t.strip() in VALID_TAGS] if tag_str else []
        records.append(VideoRecord(ref_img, seed, status, fp, ts, score, tags, lip))
    return records


def load_records(batch: str) -> tuple[List[VideoRecord], str]:
    manifest_path = Path(f"output_batch{batch}/manifest.json")
    if manifest_path.exists():
        return load_from_manifest(manifest_path), f"manifest（{manifest_path.name}）"
    md = Path(f"report_batch{batch}.md")
    if md.exists():
        return load_from_markdown(md), f"legacy markdown（{md.name}）"
    return [], ""


# ===================== 分析主逻辑 =====================

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--batch", type=str, required=True)
    args = ap.parse_args()
    batch = args.batch

    records, source = load_records(batch)
    if not records:
        print(f"❌ batch{batch} 未找到 manifest 或 report 数据")
        sys.exit(1)
    print(f"📂 数据源：{source} | 解析 {len(records)} 条")

    stat_success = [r for r in records if r.status == "SUCCESS"]
    stat_failed = [r for r in records if r.status == "FAILED"]
    stat_skipped = [r for r in records if r.status == "SKIPPED"]
    stat_read_fail = [r for r in records if r.status == "READ_FAILED"]

    scored = sorted([r for r in stat_success if r.score is not None],
                    key=lambda x: x.score, reverse=True)
    avg_score = sum(r.score for r in scored) / len(scored) if scored else 0
    top_samples = scored[:TOP_N]

    # 客观口型分统计
    lips = [r for r in stat_success if r.lipsync_score is not None]
    avg_lip = sum(r.lipsync_score for r in lips) / len(lips) if lips else None

    # 客观/主观对照（两者都有的样本）
    both = [r for r in stat_success if r.score is not None and r.lipsync_score is not None]
    diverge = [r for r in both if r.lipsync_score >= 0.6 and r.score <= 5]  # 客观高人工低

    # 耗时基线
    timed = [r for r in stat_success if r.gen_seconds]
    avg_gen = sum(r.gen_seconds for r in timed) / len(timed) if timed else None

    # 每参考图最优
    group_best = {}
    for rec in scored:
        if rec.ref_img not in group_best or rec.score > group_best[rec.ref_img].score:
            group_best[rec.ref_img] = rec
    all_best_seeds = sorted({r.seed for r in group_best.values()}, key=lambda x: int(x) if x.isdigit() else 9999)

    tag_counter = Counter(t for r in stat_success for t in r.tags)

    # ---------- 控制台 ----------
    print("=" * 70)
    print(f"📊 batch{batch} 分析（含客观口型分）")
    print("=" * 70)
    print(f"SUCCESS {len(stat_success)} | FAILED {len(stat_failed)} | SKIPPED {len(stat_skipped)} | READ_FAILED {len(stat_read_fail)}")
    print(f"📝 人工打分样本：{len(scored)} | 平均分：{avg_score:.2f}")
    if avg_lip is not None:
        print(f"🎯 客观口型分样本：{len(lips)} | 平均：{avg_lip:.3f} | 高分(≥0.6)：{sum(1 for r in lips if r.lipsync_score >= 0.6)}")
    if avg_gen:
        print(f"⏱️ 生成耗时：平均 {avg_gen:.0f}s | 最快 {min(r.gen_seconds for r in timed):.0f}s | 最慢 {max(r.gen_seconds for r in timed):.0f}s")
    print("-" * 70)
    for i, s in enumerate(top_samples, 1):
        lip = f" 口型{s.lipsync_score:.2f}" if s.lipsync_score else ""
        print(f"[{i}] {s.ref_img} | Seed {s.seed} | 人工{s.score}{lip} | 缺陷:{','.join(s.tags) or '无'}")
    if diverge:
        print("-" * 70)
        print("⚠️ 客观/主观背离样本（口型分高但人工分低 → 检查音画内容相关性，口型对≠内容对）：")
        for r in diverge:
            print(f"   {r.ref_img} | Seed {r.seed} | 口型{r.lipsync_score:.2f} vs 人工{r.score}")
    if not scored:
        print("ℹ️ 暂无人工打分。请先填写 report 的评分/缺陷标签后重跑本脚本（客观分分析不受影响）")

    # ---------- 输出 analysis_result_batchXX.md ----------
    md = [f"# batch{batch} 自动分析报告（双格式兼容）", ""]
    md.append(f"- 数据源：`{source}`")
    md.append(f"- SUCCESS {len(stat_success)} / FAILED {len(stat_failed)} / SKIPPED {len(stat_skipped)}")
    md.append(f"- 人工打分：{len(scored)} 条，平均 **{avg_score:.2f}**")
    if avg_lip is not None:
        md.append(f"- 客观口型分：{len(lips)} 条，平均 **{avg_lip:.3f}**（backend 分布：{dict(Counter(r.lipsync_backend for r in lips))}）")
    if avg_gen:
        md.append(f"- 生成耗时基线：平均 **{avg_gen:.0f}s**（区间 {min(r.gen_seconds for r in timed):.0f}~{max(r.gen_seconds for r in timed):.0f}s）")
    md.append("")

    md.append("## 缺陷频次（人工标签）")
    md.append("| 缺陷 | 次数 |")
    md.append("|------|------|")
    md.extend(f"| {t} | {c} |" for t, c in tag_counter.most_common() or [("无", 0)])
    md.append("")

    if both and len(both) >= 3:
        import statistics
        xs = [r.lipsync_score for r in both]
        ys = [r.score for r in both]
        try:
            corr = statistics.correlation(xs, ys)
            md.append(f"## 客观/主观相关性：{corr:.2f}（>0.6 说明自动初筛可信）")
            md.append("")
        except statistics.StatisticsError:
            pass

    md.append(f"## Top{TOP_N} 高分样本")
    md.append("| 排名 | 参考图 | Seed | 人工分 | 口型分 | 缺陷 | 路径 |")
    md.append("|------|--------|------|--------|--------|------|------|")
    for i, s in enumerate(top_samples, 1):
        lip = f"{s.lipsync_score:.2f}" if s.lipsync_score else "-"
        md.append(f"| {i} | {s.ref_img} | {s.seed} | {s.score} | {lip} | {','.join(s.tags) or '无'} | {s.file_path} |")
    md.append("")

    md.append("## 每张参考图最优样本")
    md.append("| 参考图 | Best Seed | 人工分 | 口型分 | 缺陷 |")
    md.append("|--------|-----------|--------|--------|------|")
    for img, r in group_best.items():
        lip = f"{r.lipsync_score:.2f}" if r.lipsync_score else "-"
        md.append(f"| {img} | {r.seed} | {r.score} | {lip} | {','.join(r.tags) or '无'} |")
    md.append("")
    md.append(f"## 推荐最优Seed清单（去重）")
    md.append(f"`{all_best_seeds}`")
    md.append("")

    out_path = Path(f"analysis_result_batch{batch}.md")
    out_path.write_text("\n".join(md), encoding="utf-8")
    print(f"\n📄 分析报告：{out_path}")
    print(f"→ 下一步：python update_seed_list.py --batch {batch}")


if __name__ == "__main__":
    main()
