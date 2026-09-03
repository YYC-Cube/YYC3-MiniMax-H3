# -*- coding: utf-8 -*-
"""
@file export_multi_batch_summary.py
@author YanYuCloudCube Team <admin@0379.email>
@version v1.1.0
@created 2026-09-02
@updated 2026-09-03
@status stable
@copyright Copyright (c) 2025-2026 YYC3 Team
@license MIT


export_multi_batch_summary.py 多批次打分汇总导出脚本
来源：MiniMax-H3-DiffSynth本地版-提示词模板.md
功能：扫描目录下所有 report_batch*.md，自动解析各批次评分，
     生成跨批次横向对比汇总表 multi_batch_summary.md，一次性对比所有seed评分变化。

兼容设计：自动识别表头列位置，无论报告是否带「预览封面」列都能正确解析；
只读取md，不修改任何已有脚本和报告。

使用方法：
  # 确保目录下有 report_batch01.md、report_batch02.md 等
  python export_multi_batch_summary.py
"""
import re
from pathlib import Path
from collections import defaultdict
from dataclasses import dataclass, field
from typing import List, Dict, Optional

# ===================== 配置区 =====================
OUTPUT_SUMMARY_MD = Path("multi_batch_summary.md")
# ==================================================


@dataclass
class Record:
    batch: str
    ref_img: str
    seed: str
    status: str
    score: Optional[float]
    tags: List[str] = field(default_factory=list)


def parse_batch_report(md_path: Path) -> List[Record]:
    """解析单个 report_batchXX.md，自动定位列索引"""
    content = md_path.read_text(encoding="utf-8")
    lines = content.splitlines()

    # 找表头行
    header_idx = None
    col_map = {}
    for i, line in enumerate(lines):
        if line.strip().startswith("|") and ("参考图" in line) and ("Seed" in line):
            header_idx = i
            headers = [h.strip() for h in line.strip().strip("|").split("|")]
            for idx, h in enumerate(headers):
                if "参考图" in h:
                    col_map["ref_img"] = idx
                elif h == "Seed":
                    col_map["seed"] = idx
                elif "状态" in h:
                    col_map["status"] = idx
                elif "评分" in h:
                    col_map["score"] = idx
                elif "缺陷" in h or "标签" in h:
                    col_map["tags"] = idx
            break

    if header_idx is None or "ref_img" not in col_map:
        print(f"⚠️ {md_path.name} 未找到有效表头，跳过")
        return []

    # 从批次文件名提取批次号
    batch_match = re.search(r"report_batch(\d+)\.md", md_path.name)
    batch = batch_match.group(1) if batch_match else "??"

    records: List[Record] = []
    for line in lines[header_idx + 1:]:
        line = line.strip()
        if not line.startswith("|"):
            continue
        if "----" in line:
            continue
        cells = [c.strip() for c in line.strip().strip("|").split("|")]
        if len(cells) <= max(col_map.values()):
            continue

        ref_img = cells[col_map["ref_img"]]
        seed = cells[col_map["seed"]]
        status = cells[col_map["status"]]

        score_str = cells[col_map["score"]] if "score" in col_map else ""
        score = None
        if score_str and score_str.replace(".", "").isdigit():
            score = float(score_str)

        tags_str = cells[col_map["tags"]] if "tags" in col_map else ""
        tags = [t.strip() for t in tags_str.split(",") if t.strip()] if tags_str else []

        records.append(Record(
            batch=batch,
            ref_img=ref_img,
            seed=seed,
            status=status,
            score=score,
            tags=tags
        ))
    return records


def main():
    # 扫描所有批次报告
    batch_files = sorted(Path(".").glob("report_batch*.md"))
    if not batch_files:
        print("❌ 未找到任何 report_batch*.md 文件")
        return

    print(f"📂 发现 {len(batch_files)} 个批次报告：")
    for f in batch_files:
        print(f"  - {f.name}")

    all_records: List[Record] = []
    for f in batch_files:
        recs = parse_batch_report(f)
        all_records.extend(recs)
        print(f"  ✅ {f.name}: 解析到 {len(recs)} 条记录")

    if not all_records:
        print("⚠️ 没有解析到任何有效记录")
        return

    # 批次列表（排序）
    batches = sorted({r.batch for r in all_records})

    # ========== 统计1：各批次总览 ==========
    batch_stats = {}
    for b in batches:
        b_recs = [r for r in all_records if r.batch == b]
        success = [r for r in b_recs if r.status == "SUCCESS"]
        failed = [r for r in b_recs if r.status == "FAILED"]
        skipped = [r for r in b_recs if r.status == "SKIPPED"]
        scored = [r for r in success if r.score is not None]
        avg = sum(r.score for r in scored) / len(scored) if scored else 0
        max_score = max((r.score for r in scored), default=0)
        batch_stats[b] = {
            "total": len(b_recs),
            "success": len(success),
            "failed": len(failed),
            "skipped": len(skipped),
            "scored": len(scored),
            "avg": avg,
            "max": max_score,
        }

    # ========== 统计2：按 (参考图, Seed) 横向对比各批次评分 ==========
    # key: (ref_img, seed), value: {batch: score}
    cross_map: Dict[tuple, Dict[str, Optional[float]]] = defaultdict(dict)
    cross_status: Dict[tuple, Dict[str, str]] = defaultdict(dict)
    cross_tags: Dict[tuple, Dict[str, List[str]]] = defaultdict(dict)

    for r in all_records:
        key = (r.ref_img, r.seed)
        cross_map[key][r.batch] = r.score
        cross_status[key][r.batch] = r.status
        cross_tags[key][r.batch] = r.tags

    # 按参考图分组排序
    ref_imgs = sorted({r.ref_img for r in all_records})

    # ========== 统计3：每个参考图在各批次的最优Seed ==========
    best_per_batch: Dict[str, Dict[str, Record]] = defaultdict(dict)
    for b in batches:
        for img in ref_imgs:
            candidates = [r for r in all_records
                          if r.batch == b and r.ref_img == img
                          and r.status == "SUCCESS" and r.score is not None]
            if candidates:
                best = max(candidates, key=lambda x: x.score)
                best_per_batch[img][b] = best

    # ========== 生成汇总 Markdown ==========
    md = []
    md.append("# 多批次打分汇总对比表")
    md.append("")
    md.append(f"> 自动生成，覆盖批次：{', '.join(batches)}")
    md.append("")

    # 表1：各批次总览
    md.append("## 1. 各批次总览")
    md.append("")
    md.append("| 批次 | 总记录 | 成功 | 失败 | 跳过 | 有效打分 | 平均分 | 最高分 |")
    md.append("|------|--------|------|------|------|----------|--------|--------|")
    for b in batches:
        s = batch_stats[b]
        md.append(f"| batch{b} | {s['total']} | {s['success']} | {s['failed']} | {s['skipped']} | {s['scored']} | {s['avg']:.2f} | {s['max']:.1f} |")
    md.append("")

    # 表2：跨批次评分横向对比（按参考图分组）
    md.append("## 2. 跨批次 Seed 评分横向对比")
    md.append("")
    md.append("> 同一参考图 + 同一 Seed 在不同批次的评分变化，空值表示该批次无此样本")
    md.append("")

    for img in ref_imgs:
        md.append(f"### 参考图：{img}")
        md.append("")
        header = "| Seed |" + "|".join(f" batch{b} 评分 | batch{b} 状态 | batch{b} 缺陷" for b in batches) + "|"
        sep = "|------|" + "|".join("------|------|------" for _ in batches) + "|"
        md.append(header)
        md.append(sep)

        # 该参考图下所有seed
        seeds_for_img = sorted({r.seed for r in all_records if r.ref_img == img},
                               key=lambda x: int(x) if x.isdigit() else 9999)
        for seed in seeds_for_img:
            key = (img, seed)
            row = f"| {seed} |"
            for b in batches:
                score = cross_map[key].get(b)
                status = cross_status[key].get(b, "-")
                tags = ",".join(cross_tags[key].get(b, [])) or "-"
                score_str = f"{score:.1f}" if score is not None else "-"
                row += f" {score_str} | {status} | {tags} |"
            md.append(row)
        md.append("")

    # 表3：各参考图每批次最优Seed
    md.append("## 3. 各参考图每批次最优 Seed")
    md.append("")
    header3 = "| 参考图 |" + "|".join(f" batch{b} 最优Seed | batch{b} 最高分" for b in batches) + "|"
    sep3 = "|--------|" + "|".join("------|------" for _ in batches) + "|"
    md.append(header3)
    md.append(sep3)
    for img in ref_imgs:
        row = f"| {img} |"
        for b in batches:
            best = best_per_batch[img].get(b)
            if best:
                row += f" {best.seed} | {best.score:.1f} |"
            else:
                row += " - | - |"
        md.append(row)
    md.append("")

    # 表4：全局Top10高分样本（跨所有批次）
    md.append("## 4. 全局 Top 10 高分样本")
    md.append("")
    all_scored = [r for r in all_records if r.score is not None and r.status == "SUCCESS"]
    all_scored.sort(key=lambda x: x.score, reverse=True)
    md.append("| 排名 | 批次 | 参考图 | Seed | 评分 | 缺陷标签 |")
    md.append("|------|------|--------|------|------|----------|")
    for i, r in enumerate(all_scored[:10], 1):
        tags = ",".join(r.tags) if r.tags else "无"
        md.append(f"| {i} | batch{r.batch} | {r.ref_img} | {r.seed} | {r.score:.1f} | {tags} |")
    md.append("")

    # 表5：缺陷标签跨批次统计
    md.append("## 5. 缺陷标签跨批次统计")
    md.append("")
    all_tags_set = set()
    for r in all_records:
        all_tags_set.update(r.tags)
    all_tags_sorted = sorted(all_tags_set)
    header5 = "| 缺陷类型 |" + "|".join(f" batch{b}" for b in batches) + "| 合计 |"
    sep5 = "|----------|" + "|".join("------" for _ in batches) + "|------|"
    md.append(header5)
    md.append(sep5)
    for tag in all_tags_sorted:
        row = f"| {tag} |"
        total = 0
        for b in batches:
            cnt = sum(1 for r in all_records if r.batch == b and tag in r.tags)
            total += cnt
            row += f" {cnt} |"
        row += f" {total} |"
        md.append(row)
    md.append("")

    # 结论与建议
    md.append("## 6. 迭代结论与建议")
    md.append("")
    # 平均分趋势
    if len(batches) >= 2:
        first_avg = batch_stats[batches[0]]["avg"]
        last_avg = batch_stats[batches[-1]]["avg"]
        diff = last_avg - first_avg
        trend = "上升" if diff > 0 else ("下降" if diff < 0 else "持平")
        md.append(f"- **平均分趋势**：batch{batches[0]} → batch{batches[-1]}，从 {first_avg:.2f} → {last_avg:.2f}，{trend} {abs(diff):.2f} 分")
    # 高频缺陷
    if all_tags_sorted:
        tag_total = {t: sum(1 for r in all_records if t in r.tags) for t in all_tags_sorted}
        top_tag = max(tag_total, key=tag_total.get)
        md.append(f"- **最高频缺陷**：{top_tag}（共 {tag_total[top_tag]} 次），下一轮应重点针对该缺陷优化 Prompt / 参考图")
    # 最优seed集合
    global_best_seeds = sorted({r.seed for r in all_scored[:5]}, key=lambda x: int(x) if x.isdigit() else 9999)
    md.append(f"- **推荐下一轮优先 Seed**：{global_best_seeds}")
    md.append("")

    OUTPUT_SUMMARY_MD.write_text("\n".join(md), encoding="utf-8")
    print(f"\n🎉 多批次汇总表已生成：{OUTPUT_SUMMARY_MD}")
    print(f"   覆盖批次：{', '.join(batches)}")
    print(f"   总记录数：{len(all_records)}")


if __name__ == "__main__":
    main()
