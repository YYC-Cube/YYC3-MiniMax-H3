# -*- coding: utf-8 -*-
"""
@file pipeline_auto.py
@author YanYuCloudCube Team <admin@0379.email>
@version v1.1.0
@created 2026-09-02
@updated 2026-09-03
@status stable
@copyright Copyright (c) 2025-2026 YYC3 Team
@license MIT


pipeline_auto.py — 一键全流程流水线 v2（批次隔离 + 自动评分节点 · Phase 1/2 改造）
来源任务：docs/04-演进规划与闭环优化机制.md

流程（v2 新增步骤③）：
  ① batch_ref2va_nf4.py   生成视频 + manifest.json
  ② score_lipsync.py      SyncNet/启发式自动口型评分（回填 manifest + report）
  ③ 人工填写 report 评分/缺陷标签
  ④ analyze_report.py     双格式分析（客观/主观对照 + 耗时基线）
  ⑤ update_seed_list.py   最优seed写回主脚本

两种模式：
- AUTO_AFTER_GENERATE=False（默认推荐）：①②后暂停等人工打分，回车继续④⑤
- AUTO_AFTER_GENERATE=True：全自动连跑（适合已提前填好上一轮report）

用法：python pipeline_auto.py [--batch 03] [--auto] [--dry-run]
  --batch N   指定批次号（默认按 report_batch* 自动递增）
  --auto      跳过人工精评暂停（控制台/API 触发时使用）
  --dry-run   演练模式：只打印执行计划，不实际执行（联调/CI 用）
"""
import argparse
import re
import subprocess
import sys
from pathlib import Path

# ====================== 配置区【按需修改】======================
SCRIPTS_DIR = Path(__file__).parent          # scripts/
TOOLS_DIR = SCRIPTS_DIR / "pipeline-tools"   # scripts/pipeline-tools/
MAIN_GENERATE_SCRIPT = SCRIPTS_DIR / "batch_ref2va_nf4.py"
SCORE_SCRIPT = SCRIPTS_DIR / "score_lipsync.py"
ANALYZE_SCRIPT = TOOLS_DIR / "analyze_report.py"
UPDATE_SEED_SCRIPT = TOOLS_DIR / "update_seed_list.py"
EXPORT_DASHBOARD_SCRIPT = TOOLS_DIR / "export_dashboard_data.py"  # ⑤' 面板数据桥（静默执行，失败不阻断）
AUTO_AFTER_GENERATE = False
# ==============================================================


def get_next_batch_id() -> int:
    pattern = re.compile(r"report_batch(\d+)\.md")
    max_b = 0
    for f in Path(".").glob("report_batch*.md"):
        m = pattern.match(f.name)
        if m:
            max_b = max(max_b, int(m.group(1)))
    return max_b + 1


def run_script(script_path: Path, desc: str, batch_id: str):
    if not script_path.exists():
        print(f"\n❌ 【{desc}】文件不存在：{script_path}")
        sys.exit(1)
    print(f"\n===== {desc} 【{script_path.name} --batch {batch_id}】 =====")
    ret = subprocess.run([sys.executable, str(script_path), "--batch", batch_id])
    if ret.returncode != 0:
        print(f"\n❌ 【{desc}】执行失败，退出码：{ret.returncode}")
        sys.exit(ret.returncode)
    print(f"✅ 【{desc}】完成\n")


def main():
    parser = argparse.ArgumentParser(description="Ref2VA 一键迭代流水线 v2")
    parser.add_argument("--batch", help="指定批次号（如 03），默认自动递增")
    parser.add_argument("--auto", action="store_true", help="跳过人工精评暂停（非交互/远程触发必加）")
    parser.add_argument("--dry-run", action="store_true", help="演练模式：只打印执行计划")
    args = parser.parse_args()

    print("=" * 80)
    print("🚀 Ref2VA 一键迭代流水线 v2（manifest + 自动口型评分）")
    print("流程：生成→自动评分→(人工精评)→分析→更新Seed")
    if args.dry_run:
        print("🧪 DRY-RUN 演练模式：仅打印计划，不实际执行")
    print("=" * 80)
    batch = args.batch or f"{get_next_batch_id():02d}"
    print(f"👉 当前批次：batch{batch}")
    if args.dry_run:
        print(f"  [dry] ① {MAIN_GENERATE_SCRIPT.name} --batch {batch}")
        print(f"  [dry] ② {SCORE_SCRIPT.name} --batch {batch}")
        if not (args.auto or AUTO_AFTER_GENERATE):
            print(f"  [dry] ⏸ 人工精评暂停（report_batch{batch}.md）")
        print(f"  [dry] ④ {ANALYZE_SCRIPT.name} --batch {batch}")
        print(f"  [dry] ⑤ {UPDATE_SEED_SCRIPT.name} --batch {batch}")
        print(f"  [dry] ⑤' {EXPORT_DASHBOARD_SCRIPT.name}")
        print(f"\n🎉 batch{batch} 演练完毕（未实际执行）")
        return

    # ① 生成（manifest + 性能基线）
    run_script(MAIN_GENERATE_SCRIPT, "① 批量视频生成", batch)
    # ② 自动口型评分（SyncNet优先，降级启发式）
    run_script(SCORE_SCRIPT, "② SyncNet自动口型评分", batch)

    if not (args.auto or AUTO_AFTER_GENERATE):
        input(f"\n⏸️ 暂停！打开 report_batch{batch}.md 填写【评分(1~10)】+【缺陷标签】。\n"
              f"   （客观口型分已自动填好，只需人工精评）填写完毕按回车继续...")

    # ④ 分析（双格式：manifest优先，含客观/主观对照与耗时基线）
    run_script(ANALYZE_SCRIPT, "④ 报告分析（客观+主观）", batch)
    # ⑤ 更新seed
    run_script(UPDATE_SEED_SCRIPT, "⑤ 更新主脚本seed_list", batch)
    # ⑤' 面板数据桥：刷新 dashboard/data/batches.json（静默执行，失败不阻断流水线）
    if EXPORT_DASHBOARD_SCRIPT.exists():
        print(f"\n----- ⑤' 刷新可视化面板数据 【{EXPORT_DASHBOARD_SCRIPT.name}】 -----")
        ret = subprocess.run([sys.executable, str(EXPORT_DASHBOARD_SCRIPT)])
        print("✅ 面板数据已刷新" if ret.returncode == 0 else "⚠️ 面板数据刷新失败（不阻断流水线）")

    print(f"\n🎉 batch{batch} 流水线执行完毕！")
    print(f"📄 manifest：output_batch{batch}/manifest.json")
    print(f"📋 分析：analysis_result_batch{batch}.md")


if __name__ == "__main__":
    main()
