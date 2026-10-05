#!/usr/bin/env python3
"""
rotate_watch_jsonl.py — 看门狗 JSONL 轮转归档（docs/21 §六 · NAS 侧归档件）

职责：防止 logs/console_watch.jsonl 无限增长（launchd 600s 周期 × 永续运行），
将超过保留窗口的记录切出为按月归档文件，并同步至 NAS（复用 archive_to_nas 的
YYC3_NAS_SSH/YYC3_NAS_BASE 约定）。

数据流：
  logs/console_watch.jsonl（主文件，保留近 --keep-days 天）
    ├─ 切出 → logs/archive/watch_YYYYMM.jsonl（本地按月归档，追加写）
    └─ rsync 整文件同步 → $YYC3_NAS_BASE/logs/watch/watch_YYYYMM.jsonl（幂等覆盖）

降级语义（对齐 archive_to_nas 惯例）：
  - NAS 不可达 → 仅本地归档，主文件照常轮转（数据零丢失）；NAS 目标为整文件
    rsync 幂等覆盖，下次 nightly ④.7 自动补传，无需待队列
  - 聚合器兼容：aggregate_watch_report 常用 24h/168h 窗口 ⊆ 本地保留窗口，互不影响

用法：
  python3 scripts/pipeline-tools/rotate_watch_jsonl.py                # 默认保留 7 天
  python3 ... --keep-days 30 --dry-run                                # 演练（只报告不动文件）
退出码：0 正常（含 NAS 跳过）/ 1 本地读写异常
"""
import argparse
import json
import subprocess
import sys
from datetime import datetime, timedelta
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
WATCH_JSONL = REPO_ROOT / "logs" / "console_watch.jsonl"
ARCHIVE_DIR = REPO_ROOT / "logs" / "archive"
NAS_SSH = __import__("os").environ.get("YYC3_NAS_SSH", "yyc3-45")
NAS_BASE = __import__("os").environ.get("YYC3_NAS_BASE", "/Volume1/yyc3_hd")


def parse_ts(line: str) -> tuple[datetime | None, dict | None]:
    try:
        rec = json.loads(line)
        return datetime.fromisoformat(rec["ts"]), rec
    except (json.JSONDecodeError, KeyError, ValueError):
        return None, None  # 坏行随最旧段归档（不在主文件常驻）


def main() -> int:
    ap = argparse.ArgumentParser(description="看门狗 JSONL 轮转归档")
    ap.add_argument("--keep-days", type=int, default=7, help="主文件保留天数（默认 7）")
    ap.add_argument("--dry-run", action="store_true", help="演练：只报告不动文件")
    args = ap.parse_args()

    if not WATCH_JSONL.exists():
        print(f"[rotate] 主文件不存在（{WATCH_JSONL}），无事可做")
        return 0

    cutoff = datetime.now().astimezone() - timedelta(days=args.keep_days)
    lines = WATCH_JSONL.read_text(encoding="utf-8").splitlines()
    keep: list[str] = []
    rot_by_month: dict[str, list[str]] = {}
    for ln in lines:
        if not ln.strip():
            continue
        dt, _ = parse_ts(ln)
        if dt is None or dt < cutoff:
            month = (dt or cutoff).strftime("%Y%m")
            rot_by_month.setdefault(month, []).append(ln)
        else:
            keep.append(ln)

    rotated = sum(len(v) for v in rot_by_month.values())
    print(f"[rotate] 总 {len(lines)} 行 → 保留 {len(keep)}（近 {args.keep_days} 天）"
          f" / 轮转 {rotated}（{len(rot_by_month)} 个月切片）")
    if args.dry_run:
        for m, v in sorted(rot_by_month.items()):
            print(f"  [dry-run] 将归档 watch_{m}.jsonl ← {len(v)} 行")
        return 0
    if not rotated:
        return 0

    # 1) 本地按月归档（追加写，幂等重跑不重复——切出行已从主文件移除）
    ARCHIVE_DIR.mkdir(parents=True, exist_ok=True)
    for month, month_lines in sorted(rot_by_month.items()):
        dest = ARCHIVE_DIR / f"watch_{month}.jsonl"
        with dest.open("a", encoding="utf-8") as f:
            f.write("\n".join(month_lines) + "\n")
        print(f"  [local] {dest.name} +{len(month_lines)} 行")

    # 2) 主文件重写为保留段（原子写防半行）
    tmp = WATCH_JSONL.with_suffix(".jsonl.tmp")
    tmp.write_text("\n".join(keep) + ("\n" if keep else ""), encoding="utf-8")
    tmp.replace(WATCH_JSONL)

    # 3) NAS 整文件幂等同步（不可达跳过——下次 ④.7 自动补传）
    for month in sorted(rot_by_month):
        src = ARCHIVE_DIR / f"watch_{month}.jsonl"
        rc = subprocess.run(
            ["rsync", "-az", "--timeout", "60", "-e", "ssh",
             str(src), f"{NAS_SSH}:{NAS_BASE}/logs/watch/"],
            capture_output=True, timeout=90)
        if rc.returncode == 0:
            print(f"  [nas] watch_{month}.jsonl → {NAS_SSH}:{NAS_BASE}/logs/watch/ ✅")
        else:
            print(f"  [nas] ⚠ {NAS_SSH} 不可达，watch_{month}.jsonl 留待下次补传"
                  f"（本地已归档，零丢失）")
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except OSError as e:
        print(f"❌ [rotate] 本地读写异常：{e}", file=sys.stderr)
        sys.exit(1)
