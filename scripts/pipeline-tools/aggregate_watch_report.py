#!/usr/bin/env python3
"""
aggregate_watch_report.py — 看门狗 JSONL 次晨聚合器（docs/21 §三）

背景：console_health_check.py 落 logs/console_watch.jsonl（一行一探测），
其 docstring 承诺「nightly 次晨报告可聚合」——本脚本即该承诺的兑现件，
由 nightly_run.sh ④.6 挂载，聚合近 24h 探测记录为 Markdown 段嵌入次晨报告。

聚合口径：
  - 探测总次数 / 模式分布（full=三探点 / landing-only=纯线上观测）
  - 本地探活：health/sse 失败次数（仅 full 模式记录）
  - agent 网关：探活 ok 次数（P3 增强探点；非 24h 常驻，窗口内缺失为正常态）
  - 线上 TTFB P95：均值/峰值 + warn 超标次数（阈 5s，与看门狗同源观测基线）

用法：
  python3 scripts/pipeline-tools/aggregate_watch_report.py                 # 近 24h → Markdown
  python3 scripts/pipeline-tools/aggregate_watch_report.py --hours 168     # 近 7 天
  python3 scripts/pipeline-tools/aggregate_watch_report.py --json          # 机器可读
退出码：0 正常（含零数据）/ 1 文件读取异常
"""
import json
import sys
from collections import Counter
from datetime import datetime, timedelta
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
LOG_FILE = REPO_ROOT / "logs" / "console_watch.jsonl"
WARN_THRESHOLD_S = 5.0  # 与 console_health_check.TTFB_P95_WARN_S 同阈


def load_records(hours: int) -> list[dict]:
    if not LOG_FILE.exists():
        return []
    since = datetime.now().astimezone() - timedelta(hours=hours)
    out = []
    with LOG_FILE.open(encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                rec = json.loads(line)
                if datetime.fromisoformat(rec["ts"]) >= since:
                    out.append(rec)
            except (json.JSONDecodeError, KeyError, ValueError):
                continue  # 坏行跳过（进程被杀可能留下半行）
    return out


def aggregate(records: list[dict]) -> dict:
    modes = Counter(r.get("mode", "full") for r in records)
    full = [r for r in records if r.get("mode") == "full"]
    health_fail = sum(1 for r in full if not (r.get("health") or {}).get("ok", False))
    sse_fail = sum(1 for r in full if not (r.get("sse") or {}).get("ok", False))
    agent_seen = sum(1 for r in full if "agent" in r)
    agent_ok = sum(1 for r in full if (r.get("agent") or {}).get("ok"))
    p95s = [r["landing"]["p95_s"] for r in records
            if isinstance((r.get("landing") or {}).get("p95_s"), (int, float))
            and r["landing"]["p95_s"] > 0]
    warn = sum(1 for r in records if (r.get("landing") or {}).get("warn"))
    return {
        "total": len(records),
        "modes": dict(modes),
        "health_fail": health_fail,
        "sse_fail": sse_fail,
        "agent_seen": agent_seen,
        "agent_ok": agent_ok,
        "p95_avg_s": round(sum(p95s) / len(p95s), 2) if p95s else None,
        "p95_max_s": max(p95s) if p95s else None,
        "warn": warn,
        "warn_threshold_s": WARN_THRESHOLD_S,
    }


def to_markdown(a: dict, hours: int) -> str:
    if not a["total"]:
        return f"看门狗聚合（近 {hours}h）：无探测记录（launchd 未挂载时仅手动/CI 触发，属正常态）"
    agent_txt = (f"{a['agent_ok']}/{a['agent_seen']} ok"
                 if a["agent_seen"] else "窗口内未探测（网关非常驻，正常态）")
    p95_txt = (f"均值 {a['p95_avg_s']}s · 峰值 {a['p95_max_s']}s"
               if a["p95_avg_s"] is not None else "—")
    return "\n".join([
        f"**看门狗聚合（近 {hours}h）**：",
        "",
        "| 指标 | 值 |",
        "| ---- | ---- |",
        f"| 探测次数 | {a['total']}（模式分布 {a['modes']}） |",
        f"| 本地探活失败 | health×{a['health_fail']} / sse×{a['sse_fail']} |",
        f"| agent 网关 | {agent_txt} |",
        f"| 线上 TTFB P95 | {p95_txt} · warn×{a['warn']}（阈 {a['warn_threshold_s']}s） |",
    ])


def main() -> int:
    args = sys.argv[1:]
    hours = int(args[args.index("--hours") + 1]) if "--hours" in args else 24
    try:
        records = load_records(hours)
    except OSError as e:
        print(f"❌ 读取失败：{LOG_FILE}（{e}）", file=sys.stderr)
        return 1
    agg = aggregate(records)
    if "--json" in args:
        print(json.dumps(agg, ensure_ascii=False, indent=2))
    else:
        print(to_markdown(agg, hours))
    return 0


if __name__ == "__main__":
    sys.exit(main())
