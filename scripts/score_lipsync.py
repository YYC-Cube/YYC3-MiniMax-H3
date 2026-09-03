# -*- coding: utf-8 -*-
"""
@file score_lipsync.py
@author YanYuCloudCube Team <admin@0379.email>
@version v1.1.0
@created 2026-09-02
@updated 2026-09-03
@status stable
@copyright Copyright (c) 2025-2026 YYC3 Team
@license MIT


score_lipsync.py — 口型同步自动评分（Phase 2 · T2.1）
来源任务：docs/04-演进规划与闭环优化机制.md

双后端策略（永不断流）：
1. syncnet（优先）：pip install syncnet-python + 官方权重（sfd_face.pth / syncnet_v2.model）
   置信度 conf≈10 为官方demo良好量级；score_norm = conf / (abs(conf)+5) ∈ (0,1)
2. heuristic（降级）：音频RMS包络 × 口型区运动能量的分桶相关系数，[-1,1] → [0,1]
   仅需 ffmpeg + opencv，无需下载权重

职责：
- 读取 output_batchXX/manifest.json
- 对每条 SUCCESS 记录的视频打分
- 回填 manifest.records[].lipsync（原子保存）
- 同步刷新 report_batchXX.md 的「口型分」列

用法：python score_lipsync.py --batch 01 [--force] [--backend heuristic]
"""
import argparse
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / "lib"))
from h3_common import Manifest, heuristic_sync_score, now_iso, syncnet_score

VALID_TAGS_NOTE = "（口型分：SyncNet置信度归一化或启发式音画相关，0~1，越高越同步）"


def parse_args():
    ap = argparse.ArgumentParser(description="SyncNet 口型自动评分")
    ap.add_argument("--batch", type=str, required=True, help="批次号，例如 01")
    ap.add_argument("--force", action="store_true", help="重评已有 lipsync 的样本")
    ap.add_argument("--backend", choices=["auto", "syncnet", "heuristic"], default="auto",
                    help="auto=优先syncnet降级heuristic；指定则强制")
    return ap.parse_args()


def refresh_report(md_path: Path, manifest: Manifest):
    """用 manifest 全量重写 report 表格（保留头部信息与人工列逻辑由 analyze 处理）"""
    if not md_path.exists():
        return
    lines = md_path.read_text(encoding="utf-8").splitlines()
    # 找表头行
    header_idx = None
    for i, line in enumerate(lines):
        if line.startswith("| 参考图 |") or line.startswith("| 预览封面 |"):
            header_idx = i
            break
    if header_idx is None:
        return

    header = "| 参考图 | Seed | 状态 | 视频相对路径 | 时间 | 口型分 | 评分(1~10) | 缺陷标签 |"
    sep = "|--------|------|------|--------------|------|--------|------------|----------|"
    rows = []
    for r in manifest.flat_rows():
        lip = r["lipsync_score"]
        lip_str = f"{lip:.2f}" if isinstance(lip, (int, float)) else "-"
        rows.append(f"| {r['ref_img']} | {r['seed']} | {r['status']} | `{r['video_path']}` | {r['time']} | {lip_str} |  |  |")

    new_lines = lines[:header_idx] + [header, sep] + rows
    # 保留表格之后的附加内容（如闭环框架）若有
    md_path.write_text("\n".join(new_lines) + "\n", encoding="utf-8")


def main():
    args = parse_args()
    output_root = Path(f"output_batch{args.batch}")
    manifest_path = output_root / "manifest.json"
    report_md = Path(f"report_batch{args.batch}.md")

    if not manifest_path.exists():
        print(f"❌ manifest 不存在：{manifest_path}，请先运行 batch_ref2va_nf4.py --batch {args.batch}")
        sys.exit(1)

    manifest = Manifest.load(manifest_path)
    success_recs = [r for r in manifest.records if r["status"] == "SUCCESS"]
    todo = [r for r in success_recs
            if args.force or not r.get("lipsync")]
    print(f"📊 batch{args.batch}：SUCCESS {len(success_recs)} 条，待评分 {len(todo)} 条（--force 可重评）")
    if not todo:
        refresh_report(report_md, manifest)
        print("无待评分样本，report 已同步刷新")
        return

    # 后端探测（一次即可）
    backend = args.backend
    if backend == "auto":
        try:
            from syncnet_python import SyncNetPipeline  # noqa: F401
            backend = "syncnet"
            print("🧠 后端：SyncNet（检测到 syncnet_python）")
        except ImportError:
            backend = "heuristic"
            print("⚠️ syncnet_python 未安装，降级为启发式音画相关后端")
            print("   提示：pip install syncnet-python 并下载权重后可用 --backend auto 获得官方置信度")

    work_dir = output_root / "_scoring_work"
    done = 0
    for rec in todo:
        vp = Path(rec["video_path"])
        if not vp.exists():
            print(f"⏭️ 视频缺失，跳过：{vp}")
            continue
        print(f"🎯 {rec['ref_img']} | seed {rec['seed']} ...", end=" ", flush=True)

        if backend == "syncnet":
            result = syncnet_score(vp, work_dir)
            if result is None:  # syncnet运行失败（权重缺失等），降级
                print("syncnet失败 → heuristic")
                result = heuristic_sync_score(vp, work_dir)
        else:
            result = heuristic_sync_score(vp, work_dir)

        manifest.set_lipsync(rec["ref_img"], rec["seed"],
                             backend=result["backend"],
                             confidence=result["confidence"],
                             av_offset=result["av_offset"],
                             score_norm=result["score_norm"])
        manifest.save()
        done += 1
        sn = result.get("score_norm")
        print(f"{result['backend']} conf={result.get('confidence')} score_norm={sn}")

    refresh_report(report_md, manifest)
    print(f"\n🎉 完成 {done}/{len(todo)} 条评分")
    print(f"📄 manifest 已回填：{manifest_path}")
    print(f"📋 report 口型分列已刷新：{report_md} {VALID_TAGS_NOTE}")
    print(f"→ 下一步：人工打开 {report_md} 填写 评分/缺陷标签，然后 python analyze_report.py --batch {args.batch}")


if __name__ == "__main__":
    main()
