#!/usr/bin/env python3
"""
console_health_check.py — 工作台生产看门狗（终审遗留 P2-告警落地）

探活矩阵：
  1. BFF /api/health      → 可用性（HTTP 200 + ok:true）
  2. SSE /api/pipeline/stream → 首事件时延（连接活性，>5s 判超时）
  3. 线上 https://h3.yyc3.top → TTFB 采样 ×N，P95 记录（P3 抖动观测，数据驱动决策）

输出：logs/console_watch.jsonl（一行一探测，nightly 次晨报告可聚合）
退出码：0 全过 / 1 本地探活失败（cron 可配告警钩子）/ 2 仅线上抖动超标（不告警只记录）

用法：
  python3 scripts/pipeline-tools/console_health_check.py            # 默认本地 127.0.0.1:3030
  CONSOLE_URL=http://100.65.x.x:3030 python3 ...                    # 指定部署侧
  python3 scripts/pipeline-tools/console_health_check.py --quiet    # cron 静默（仅失败输出）
"""
import json
import os
import sys
import time
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

CONSOLE_URL = os.environ.get("CONSOLE_URL", "http://127.0.0.1:3030")
AGENT_URL = os.environ.get("AGENT_URL", "http://127.0.0.1:8300")  # agent 网关（引擎层心脏，P3 增强探点）
LANDING_URL = "https://h3.yyc3.top"
LOG_FILE = Path(__file__).resolve().parents[2] / "logs" / "console_watch.jsonl"
SSE_TIMEOUT_S = 5.0
TTFB_SAMPLES = int(os.environ.get("WATCH_TTFB_SAMPLES", "5"))
TTFB_P95_WARN_S = 5.0  # 线上 P95 超过此值记 warn（不告警，观测基线）


def log(record: dict) -> None:
    LOG_FILE.parent.mkdir(parents=True, exist_ok=True)
    with LOG_FILE.open("a", encoding="utf-8") as f:
        f.write(json.dumps(record, ensure_ascii=False) + "\n")


def ts() -> str:
    return datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")


def probe_health() -> tuple[bool, float]:
    """BFF /api/health：HTTP 200 + JSON ok:true"""
    start = time.monotonic()
    try:
        with urllib.request.urlopen(f"{CONSOLE_URL}/api/health", timeout=5) as r:
            ok = r.status == 200 and json.loads(r.read()).get("ok") is True
        return ok, time.monotonic() - start
    except Exception:
        return False, time.monotonic() - start


def probe_sse() -> tuple[bool, float]:
    """SSE 首事件：读到首行 event: 即活（SSETimeout 处理器无鉴权只读流）"""
    start = time.monotonic()
    try:
        req = urllib.request.Request(f"{CONSOLE_URL}/api/pipeline/stream")
        with urllib.request.urlopen(req, timeout=SSE_TIMEOUT_S) as r:
            head = r.read(64).decode("utf-8", errors="ignore")
            ok = r.status == 200 and head.startswith("event:")
        return ok, time.monotonic() - start
    except Exception:
        return False, time.monotonic() - start


def probe_agent() -> dict:
    """agent 网关 /api/healthz（引擎层心脏，docs/21 §一链路 ③）。

    网关为会话式常驻（B2/漫剧会话时启动），非常驻=正常态：
    探活结果仅记录（record.agent），不计入退出码判定——避免未起网关时看门狗误报。
    """
    start = time.monotonic()
    try:
        with urllib.request.urlopen(f"{AGENT_URL}/api/healthz", timeout=3) as r:
            data = json.loads(r.read())
            return {"ok": r.status == 200 and data.get("status") == "ok",
                    "claim_ready": bool(data.get("claim_ready")),
                    "transport": data.get("transport"),
                    "seconds": round(time.monotonic() - start, 3)}
    except Exception:
        return {"ok": False, "seconds": round(time.monotonic() - start, 3)}


def probe_landing_p95() -> tuple[float, list[float]]:
    """线上落地页 TTFB 采样 → (P95, 全样本)；网络不可达样本记 -1"""
    samples = []
    for _ in range(TTFB_SAMPLES):
        start = time.monotonic()
        try:
            req = urllib.request.Request(LANDING_URL, method="HEAD")
            with urllib.request.urlopen(req, timeout=15) as r:
                if r.status == 200:
                    samples.append(round(time.monotonic() - start, 3))
                else:
                    samples.append(-1.0)
        except Exception:
            samples.append(-1.0)
        time.sleep(0.3)
    valid = sorted(s for s in samples if s > 0)
    p95 = valid[max(0, int(len(valid) * 0.95) - 1)] if valid else -1.0
    return p95, samples


def main() -> int:
    quiet = "--quiet" in sys.argv
    landing_only = "--landing-only" in sys.argv  # 纯线上观测模式（本地 BFF 未常驻时零误报）

    if landing_only:
        p95, samples = probe_landing_p95()
        record = {"ts": ts(), "mode": "landing-only",
                  "landing": {"p95_s": p95, "samples": samples, "warn": p95 > TTFB_P95_WARN_S}}
        log(record)
        if not quiet:
            print(json.dumps(record, ensure_ascii=False, indent=2))
        if p95 < 0:
            print(f"❌ [console-watch] 线上探活失败：{LANDING_URL}", file=sys.stderr)
            return 1
        if p95 > TTFB_P95_WARN_S:
            print(f"⚠ [console-watch] 线上 TTFB P95={p95}s 超观测基线 {TTFB_P95_WARN_S}s", file=sys.stderr)
            return 2
        return 0

    health_ok, health_ms = probe_health()
    sse_ok, sse_ms = probe_sse()
    p95, samples = probe_landing_p95()

    record = {
        "ts": ts(),
        "console": CONSOLE_URL,
        "health": {"ok": health_ok, "seconds": round(health_ms, 3)},
        "sse": {"ok": sse_ok, "ttfb_s": round(sse_ms, 3)},
        "agent": probe_agent(),  # P3 增强探点（docs/21 §一）：仅记录不判失败（网关非常驻）
        "landing": {"p95_s": p95, "samples": samples, "warn": p95 > TTFB_P95_WARN_S},
    }
    log(record)

    if not quiet:
        print(json.dumps(record, ensure_ascii=False, indent=2))

    if not (health_ok and sse_ok):
        print(
            f"❌ [console-watch] 本地探活失败：health={health_ok} sse={sse_ok}（{CONSOLE_URL}）",
            file=sys.stderr,
        )
        return 1
    if p95 > TTFB_P95_WARN_S:
        print(f"⚠ [console-watch] 线上 TTFB P95={p95}s 超观测基线 {TTFB_P95_WARN_S}s（记录不告警）", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
