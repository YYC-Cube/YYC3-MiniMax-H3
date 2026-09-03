# -*- coding: utf-8 -*-
"""
@file update_seed_list.py
@author YanYuCloudCube Team <admin@0379.email>
@version v1.1.0
@created 2026-09-02
@updated 2026-09-03
@status stable
@copyright Copyright (c) 2025-2026 YYC3 Team
@license MIT


独立脚本 update_seed_list.py：自动读取analysis_result.md，把最优seed写入主批量脚本
来源：MiniMax-H3-DiffSynth本地版-提示词模板.md
功能：
1. 读取 analysis_result.md，提取【推荐最优Seed清单】
2. 自动找到主生成脚本（可配置脚本文件名）
3. 自动替换脚本里的 seed_list = [xxx]
4. 生成备份 xxx.bak，防止原脚本丢失

⚠️ 约束：主脚本里必须保留这一行原样写法：seed_list = [数字,数字...]，不能拆多行
运行：python update_seed_list.py
"""
import re
from pathlib import Path

# ===================== 配置区 =====================
# 分析结果文件
ANALYSIS_MD = Path("analysis_result.md")
# 你的批量生成主脚本，按需改成 NF4 或者 Pruned 的py文件名
MAIN_SCRIPT = Path("batch_ref2va_nf4.py")
# MAIN_SCRIPT = Path("batch_ref2va_pruned.py")
# =================================================


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
    # 正则匹配 seed_list = [xxx]
    pat = re.compile(r"(seed_list\s*=\s*)\[.*?\]")
    new_line = rf"\1{new_seed_list}"
    new_src = pat.sub(new_line, src)
    # 备份原脚本
    bak_file = script_path.with_suffix(".bak")
    script_path.write_text(src, encoding="utf-8")
    bak_file.write_text(src, encoding="utf-8")
    # 写入更新后脚本
    script_path.write_text(new_src, encoding="utf-8")
    return True


def main():
    best_seeds = extract_best_seeds(ANALYSIS_MD)
    if best_seeds is None:
        return
    print(f"✅ 提取到最优Seed列表：{best_seeds}")
    if not MAIN_SCRIPT.exists():
        print(f"❌ 主脚本文件 {MAIN_SCRIPT} 不存在！")
        return
    ok = replace_seed_in_script(MAIN_SCRIPT, best_seeds)
    if ok:
        print(f"\n🎉 成功更新 {MAIN_SCRIPT.name} 的 seed_list！")
        print(f"📌 原脚本已备份：{MAIN_SCRIPT.name}.bak")
        print(f"新seed_list = {best_seeds}")
    else:
        print("❌ 更新失败")


if __name__ == "__main__":
    main()
