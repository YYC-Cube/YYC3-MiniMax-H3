# -*- coding: utf-8 -*-
"""
@file clean_batch.py
@author YanYuCloudCube Team <admin@0379.email>
@version v1.1.0
@created 2026-09-02
@updated 2026-09-03
@status stable
@copyright Copyright (c) 2025-2026 YYC3 Team
@license MIT


clean_batch.py 批次清理脚本
来源：MiniMax-H3-DiffSynth本地版-提示词模板.md
功能：只删除批次output视频文件夹（含封面），**保留所有report/analysis的md打分文件**
用法：
  python clean_batch.py --batch 01   # 删除batch01视频（保留report_batch01.md）
  python clean_batch.py              # 删除所有批次output视频文件夹（全部md保留）
"""
import argparse
from pathlib import Path
import shutil


def clean_batch(batch_id: str):
    folder = Path(f"output_batch{batch_id}")
    if not folder.exists():
        print(f"⚠️ 批次 {batch_id} 的output目录不存在：{folder}")
        return
    confirm = input(f"⚠️ 确认删除 {folder} 内所有视频与封面？md报告将保留！输入y确认：")
    if confirm.lower() == "y":
        shutil.rmtree(folder)
        print(f"✅ 已删除 {folder}，报告md文件保留")
    else:
        print("❌ 取消删除")


def clean_all():
    """一键清理全部output_batch文件夹，保留所有md"""
    confirm = input("⚠️ 确认删除所有 output_batchXX 文件夹？所有report/analysis md保留！输入y确认：")
    if confirm.lower() != "y":
        print("❌ 取消批量清理")
        return
    for folder in Path(".").glob("output_batch*"):
        if folder.is_dir():
            shutil.rmtree(folder)
            print(f"✅ 删除：{folder.name}")
    print("🎉 全部output目录清理完成，md报告保留")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="清理批次output视频文件夹，保留md打分报告")
    parser.add_argument("--batch", type=str, default=None, help="指定批次，例如 01；不填则触发清理全部output")
    args = parser.parse_args()
    if args.batch:
        clean_batch(args.batch)
    else:
        clean_all()
