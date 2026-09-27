#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
@file reconcile_batches.py
@author YanYuCloudCube Team <admin@0379.email>
@version v1.0.0
@created 2026-09-27
@status active
@copyright Copyright (c) 2025-2026 YYC3 Team
@license MIT

reconcile_batches.py — 僵尸批次收敛器（TaskClear）

设计借鉴：数字人项目 ly_crontab.TaskClearCrontab（每 5min 清理异常任务，见
数字人数据库备份 www_0379_love ly_crontab id=9 实配）。H3 侧要解决的实证缺口：
2026-09-27 batch1000 seed10 在 08:00:53 被 SIGTERM 杀死（扩散 41/50），
batch_ref2va_nf4.py 的 manifest.finish() 未执行 → ended_at 永远为 null，
面板把该批次永久显示为 running，且失败 seed 无终态、无重试入口。

收敛规则（只追加、不回改原始事实）：
  对 ended_at=null 的 manifest：
    ① 仍有对应 --batch N 的 batch_ref2va_nf4.py 存活进程 → 真 running，跳过
    ② 无存活进程 → 僵尸：有 SUCCESS 记录 → partial；无 → failed
       追加 reconciled 块（at/status/reason/by/retry_hint），ended_at 保持 null
       （保留「生成器未正常结束」的事实），先备份再原子写。
  断点续跑天然支持重试：重跑同批次时 SUCCESS seed 自动跳过（anewTask 语义）。

用法：
  python scripts/pipeline-tools/reconcile_batches.py            # 干跑：只报告不写入
  python scripts/pipeline-tools/reconcile_batches.py --apply    # 执行收敛（备份+原子写）
  python scripts/pipeline-tools/reconcile_batches.py --check    # CI：存在僵尸 exit 1

建议安装（crontab -e；窗口结束后 10min 兜底，夜间流水线内亦有同名 stage 双保险）：
  10 8 * * * cd /path/to/YYC3-MiniMax-H3 && \
    /opt/miniconda3/envs/h3-m4/bin/python scripts/pipeline-tools/reconcile_batches.py --apply \
    >> logs/reconcile.log 2>&1
"""
from __future__ import annotations

import argparse
import json
import shlex
import subprocess
import sys
from datetime import datetime
from pathlib import Path

TOOLS_DIR = Path(__file__).resolve().parent          # scripts/pipeline-tools/
REPO_ROOT = TOOLS_DIR.parent.parent
BY = "reconcile_batches.py v1.0.0"


def log(msg: str) -> None:
    print(f"[{datetime.now().strftime('%F %T')}] [reconcile] {msg}", flush=True)


def find_manifests() -> list[Path]:
    return sorted(
        p for d in REPO_ROOT.glob("output_batch*")
        if (p := d / "manifest.json").exists()
    )


def live_generator_batches() -> set[str]:
    """从 ps 提取正在运行的 batch_ref2va_nf4.py 的 --batch 号集合。

    仅认生成脚本本体（pipeline_auto 会在①结束时立即拿到 ended_at；
    video_task_runner 走 importlib 且工作目录在 ~/yyc3-video-tasks，不写仓库 output_batch*）。
    """
    batches: set[str] = set()
    try:
        out = subprocess.run(["ps", "-axo", "command="], capture_output=True,
                             text=True, timeout=15).stdout
    except Exception as e:
        log(f"⚠️ ps 读取失败，按「无存活进程」处理可能误判，本次中止写入判定：{e}")
        return {"__ps_error__"}  # 哨兵：使调用方全部按活跃处理（宁漏杀不误杀）
    for line in out.splitlines():
        if "batch_ref2va_nf4.py" not in line:
            continue
        try:
            argv = shlex.split(line)
        except ValueError:
            continue
        for i, tok in enumerate(argv):
            if tok == "--batch" and i + 1 < len(argv):
                batches.add(str(argv[i + 1]).lstrip("0") or "0")
    return batches


def classify(records: list[dict]) -> str:
    return "partial" if any(r.get("status") == "SUCCESS" for r in records) else "failed"


def atomic_write(path: Path, data: dict) -> None:
    tmp = path.with_suffix(".json.tmp")
    tmp.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    tmp.replace(path)  # 与 h3_common.Manifest.save 同款原子写


def main() -> int:
    ap = argparse.ArgumentParser(description="H3 僵尸批次收敛器（TaskClear）")
    ap.add_argument("--apply", action="store_true", help="执行写入（默认仅干跑报告）")
    ap.add_argument("--check", action="store_true", help="存在未收敛僵尸时 exit 1（CI 用）")
    ap.add_argument("--reason", default="process_gone",
                    help="收敛原因标记（process_gone|window_timeout|manual）")
    args = ap.parse_args()
    if args.apply and args.check:
        print("❌ --apply 与 --check 互斥", file=sys.stderr)
        return 2

    manifests = find_manifests()
    if not manifests:
        log("未发现 output_batch*/manifest.json，无事可做")
        return 0

    live = live_generator_batches()
    if "__ps_error__" in live:
        return 2  # ps 异常：宁漏不误（见函数注释）

    zombies: list[tuple[Path, dict, str]] = []  # (manifest_path, data, new_status)
    n_done, n_running, n_already = 0, 0, 0
    for mf in manifests:
        try:
            data = json.loads(mf.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError) as e:
            log(f"⚠️ 跳过损坏 manifest：{mf}（{e}）")
            continue
        batch = str(data.get("batch", "?"))
        if data.get("ended_at"):
            n_done += 1
            continue
        if data.get("reconciled"):
            n_already += 1
            continue
        # 批次号归一比较（生成脚本可能收到 "1000" 或 "00"，ps 侧已做 lstrip）
        norm = batch.lstrip("0") or "0"
        if norm in live or batch in live:
            n_running += 1
            log(f"▶ batch{batch} 生成进程存活，确认为真 running，跳过")
            continue
        status = classify(data.get("records", []))
        zombies.append((mf, data, status))
        log(f"🧟 batch{batch} ended_at=null 且无存活生成进程 → 判定僵尸（{status}）")

    log(f"扫描完毕：正常结束 {n_done}｜运行中 {n_running}｜已收敛 {n_already}｜"
        f"待收敛僵尸 {len(zombies)}")

    if args.check:
        if zombies:
            log(f"❌ --check：存在 {len(zombies)} 个未收敛僵尸批次")
            return 1
        log("✅ --check：无僵尸批次")
        return 0

    if not args.apply:
        if zombies:
            log("🧪 干跑模式（默认）：未写入。确认后加 --apply 执行收敛")
        return 0

    for mf, data, status in zombies:
        batch = str(data.get("batch", "?"))
        ts = datetime.now().strftime("%Y%m%d-%H%M%S")
        backup = mf.with_name(f"manifest.json.bak-{ts}")
        backup.write_bytes(mf.read_bytes())  # 先备份（收敛可回滚）
        data["reconciled"] = {
            "at": datetime.now().isoformat(timespec="seconds"),
            "status": status,
            "reason": args.reason,
            "by": BY,
            "retry_hint": (
                f"python scripts/batch_ref2va_nf4.py --batch {batch}"
                f"  # 断点续跑：SUCCESS seed 自动跳过，仅补跑失败/缺失 seed"
            ),
        }
        atomic_write(mf, data)
        log(f"✅ batch{batch} 已收敛为 {status}（备份 {backup.name}）")

    log("收敛完成；请运行 python scripts/pipeline-tools/export_dashboard_data.py 刷新面板")
    return 0


if __name__ == "__main__":
    sys.exit(main())
