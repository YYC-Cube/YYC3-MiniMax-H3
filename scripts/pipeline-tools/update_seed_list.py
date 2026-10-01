# -*- coding: utf-8 -*-
"""
@file update_seed_list.py
@author YanYuCloudCube Team <admin@0379.email>
@version v1.2.0
@created 2026-09-02
@updated 2026-10-02
@status stable
@copyright Copyright (c) 2025-2026 YYC3 Team
@license MIT


独立脚本 update_seed_list.py：自动读取 analysis_result_batch{N}.md，把最优seed写入主批量脚本
来源：MiniMax-H3-DiffSynth本地版-提示词模板.md
功能：
1. 读取最新的 analysis_result_batch{N}.md（可用 --batch N 指定），提取【推荐最优Seed清单】
2. 自动找到主生成脚本（可配置脚本文件名）
3. 自动替换脚本里的 seed_list/SEED_LIST = [xxx]（大小写均可，保留原变量名）
4. 生成备份 xxx.bak，防止原脚本丢失
5. 推荐清单为空（夜批无人工打分）时跳过写回并 exit 0——保留现有种子表，不误清空
6. 真实失败（文件缺失/解析失败/脚本缺失）exit 1，由 pipeline_auto stage ⑤ 显式标红
   （v1.1.0 及以前：路径写死旧名 analysis_result.md、正则不匹配 SEED_LIST、失败仍 exit 0
    ——三重静默失效，2026-10-02 batch1005 晨检定位）

⚠️ 约束：主脚本里必须保留这一行原样写法：seed_list = [数字,数字...]，不能拆多行
运行：python update_seed_list.py
"""
import re
from pathlib import Path

# ===================== 配置区 =====================
# 分析结果文件：默认取仓库根最新的 analysis_result_batch{N}.md，可用 --batch N 指定
REPO_ROOT = Path(__file__).resolve().parent.parent.parent
# 你的批量生成主脚本，按需改成 NF4 或者 Pruned 的py文件名
MAIN_SCRIPT = REPO_ROOT / "scripts" / "batch_ref2va_nf4.py"
# MAIN_SCRIPT = REPO_ROOT / "scripts" / "batch_ref2va_pruned.py"
# =================================================


def resolve_analysis_md(batch=None):
    """定位 analysis_result_batch{N}.md（--batch 指定或取最新 mtime），找不到返回 None"""
    if batch is not None:
        p = REPO_ROOT / f"analysis_result_batch{batch}.md"
        return p if p.exists() else None
    cands = sorted(REPO_ROOT.glob("analysis_result_batch*.md"), key=lambda p: p.stat().st_mtime)
    return cands[-1] if cands else None


def extract_best_seeds(md_path: Path):
    """从 analysis_result.md 提取最优seed列表"""
    if not md_path.exists():
        print(f"❌ {md_path} 不存在，请先运行 analyze_report.py")
        return None
    content = md_path.read_text(encoding="utf-8")
    # 匹配 `[42,24,66]` 格式
    pattern = re.compile(r"推荐最优Seed清单（去重）\n`(\[.*?\])`")
    match = pattern.search(content)
    if not match:
        print("❌ 未找到最优Seed清单，请确认analysis_result.md已正常生成")
        return None
    seed_str = match.group(1)
    try:
        seed_list = eval(seed_str)
        if not isinstance(seed_list, list):
            raise ValueError("不是列表")
        # 全部转为int，去重+排序
        seed_list = sorted(list({int(s) for s in seed_list}))
        return seed_list
    except Exception as e:
        print(f"❌ Seed解析失败：{e}")
        return None


def replace_seed_in_script(script_path: Path, new_seed_list):
    # 读取原脚本
    src = script_path.read_text(encoding="utf-8")
    # 正则匹配模块级 seed_list/SEED_LIST = [xxx]（行首锚定，避免误伤 main() 内缩进的同名赋值）
    pat = re.compile(r"^((?:seed_list|SEED_LIST)\s*=\s*)\[.*?\]", re.MULTILINE)
    if not pat.search(src):
        print(f"❌ {script_path.name} 中未找到 seed_list/SEED_LIST 单行定义")
        return False
    new_line = rf"\g<1>{new_seed_list}"
    new_src = pat.sub(new_line, src)
    # 备份原脚本（旧内容）再写入新内容
    bak_file = script_path.with_suffix(".bak")
    bak_file.write_text(src, encoding="utf-8")
    script_path.write_text(new_src, encoding="utf-8")
    return True


def main():
    import argparse
    ap = argparse.ArgumentParser(description="把 analysis_result_batch{N}.md 的最优seed写回主脚本")
    ap.add_argument("--batch", type=int, default=None, help="指定批次号（默认取最新 analysis_result_batch*.md）")
    args = ap.parse_args()

    md_path = resolve_analysis_md(args.batch)
    if md_path is None:
        print("❌ 仓库根未找到任何 analysis_result_batch*.md，请先运行 analyze_report.py")
        return 1
    best_seeds = extract_best_seeds(md_path)
    if best_seeds is None:
        return 1
    if not best_seeds:
        # 夜批无人工打分时推荐清单为空：保留现有种子表，不算失败（设计内跳过）
        print(f"⏭️ {md_path.name} 推荐清单为空（待人工打分），跳过写回，保留现有种子表")
        return 0
    print(f"✅ 提取到最优Seed列表：{best_seeds}（来源 {md_path.name}）")
    if not MAIN_SCRIPT.exists():
        print(f"❌ 主脚本文件 {MAIN_SCRIPT} 不存在！")
        return 1
    ok = replace_seed_in_script(MAIN_SCRIPT, best_seeds)
    if ok:
        print(f"\n🎉 成功更新 {MAIN_SCRIPT.name} 的 seed_list！")
        print(f"📌 原脚本已备份：{MAIN_SCRIPT.name}.bak")
        print(f"新seed_list = {best_seeds}")
        return 0
    print("❌ 更新失败")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
