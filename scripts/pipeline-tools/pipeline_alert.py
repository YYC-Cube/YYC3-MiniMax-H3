#!/usr/bin/env python3
# ==============================================================
# 流水线异常告警与聚合升级工具 v1.0（doc 10/12/13 落地件）
# @file scripts/pipeline-tools/pipeline_alert.py
# @author Intelligent Application Implementation Expert <admin@0379.email>
# @version v1.0.0
# @created 2026-09-26
#
# 职责（三合一，对齐生产闭环蓝图）：
#   doc10 通知：扫描最新批次 manifest → 分级（OK/WARN/BLOCKED）→ 企微 webhook 推送
#   doc12 聚合：指纹去重 + 静默窗口 + 连续 N 次升级（告警抑制防轰炸，升级时 @提醒）
#   doc13 工单：BLOCKED 或升级触发时调用 ALERT_TICKET_CMD（argv 注入 JSON，零 shell）
# 环境变量：
#   WECOM_WEBHOOK_URL  企微机器人地址（缺省=dry-run 只打印不发送）
#   ALERT_TICKET_CMD   工单对接命令（可选，BLOCKED/升级时以 argv[1]=JSON 调用）
#   H3_ALERT_QUIET_H   同指纹同级别静默窗口小时数（默认 6）
#   H3_ALERT_ESCALATE  连续出现 N 次升级（默认 3）
# 用法：
#   python3 scripts/pipeline-tools/pipeline_alert.py                # 自动扫最新批次
#   python3 scripts/pipeline-tools/pipeline_alert.py --batch 92   # 指定批次
#   python3 scripts/pipeline-tools/pipeline_alert.py --send       # 强制要求 webhook
# 退出码：0=OK  1=告警已发（含 dry-run）  2=BLOCKED（含工单失败不计）
# ==============================================================
import argparse
import json
import os
import subprocess
import sys
import time
import urllib.request
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
STATE_PATH = REPO_ROOT / "logs" / "alert_state.json"
QUIET_H = float(os.getenv("H3_ALERT_QUIET_H", "6"))
ESCALATE_N = int(os.getenv("H3_ALERT_ESCALATE", "3"))


def latest_batch() -> str | None:
    batches = sorted(
        (int(p.name.removeprefix("output_batch")) for p in REPO_ROOT.glob("output_batch*")
         if p.name.removeprefix("output_batch").isdigit() and (p / "manifest.json").exists()))
    return str(batches[-1]) if batches else None


def assess(batch: str) -> dict:
    """分级：manifest 缺失/损坏=BLOCKED；FAILED>0=WARN；全部 SUCCESS=OK"""
    mf = REPO_ROOT / f"output_batch{batch}" / "manifest.json"
    if not mf.exists():
        return {"batch": batch, "severity": "BLOCKED", "reason": f"manifest 缺失：{mf.name}"}
    try:
        m = json.loads(mf.read_text(encoding="utf-8"))
    except json.JSONDecodeError as e:
        return {"batch": batch, "severity": "BLOCKED", "reason": f"manifest 损坏：{e}"}
    records = m.get("records", [])
    failed = [r for r in records if r.get("status") not in ("SUCCESS", "SKIPPED")]
    sev = "OK" if not failed else "WARN"
    return {"batch": batch, "severity": sev, "total": len(records),
            "failed": len(failed),
            "failed_seeds": [r.get("seed") for r in failed][:10],
            "reason": (f"{len(failed)}/{len(records)} 条 FAILED"
                       if failed else "全部 SUCCESS")}


def should_notify(state: dict, fingerprint: str, severity: str) -> tuple[bool, int]:
    """doc12 聚合：静默窗口内同指纹同级别不重发；返回 (是否发送, 已连续次数)"""
    now = time.time()
    rec = state.setdefault(fingerprint, {"last": 0.0, "sev": "", "count": 0})
    quiet_passed = now - rec["last"] > QUIET_H * 3600
    count = rec["count"] + 1
    if rec["sev"] == severity and not quiet_passed:
        rec["count"] = count
        return False, count
    rec.update({"last": now, "sev": severity, "count": count})
    return True, count


def render_markdown(a: dict, count: int, upgraded: bool) -> str:
    tag = {"OK": "✅", "WARN": "⚠️", "BLOCKED": "🚨"}[a["severity"]]
    lines = [f"### {tag} H3 流水线告警 [{a['severity']}]",
             f"> 批次：batch{a['batch']}｜连续第 {count} 次｜{time.strftime('%m-%d %H:%M')}",
             f"> 摘要：{a['reason']}"]
    if upgraded:
        lines.insert(1, "**@告警升级**：已达连续阈值，请值班同学介入")
    if a.get("failed_seeds"):
        lines.append(f"> 失败 seeds：{a['failed_seeds']}")
    return "\n".join(lines)


def deliver(md: str, args) -> None:
    webhook = os.getenv("WECOM_WEBHOOK_URL", "")
    if not webhook:
        print(f"[DRY-RUN] 未配置 WECOM_WEBHOOK_URL，仅打印：\n{md}")
        if args.send:
            sys.exit("❌ --send 要求 WECOM_WEBHOOK_URL 已配置")
        return
    body = json.dumps({"msgtype": "markdown", "markdown": {"content": md}}).encode()
    req = urllib.request.Request(webhook, data=body,
                                 headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=10) as r:
        print(f"[企微] 推送返回：{r.read().decode()[:120]}")


def open_ticket(payload: dict) -> None:
    """doc13 工单对接：argv 注入 JSON（铁律④ 零 shell）；命令由运维配置"""
    cmd = os.getenv("ALERT_TICKET_CMD", "")
    if not cmd:
        print("[工单] 未配置 ALERT_TICKET_CMD，跳过（可配飞书/禅道等提单命令）")
        return
    subprocess.run([*cmd.split(), json.dumps(payload, ensure_ascii=False)],
                   cwd=REPO_ROOT, timeout=30, check=False)
    print(f"[工单] 已调用：{cmd}")


def main() -> int:
    ap = argparse.ArgumentParser(description="H3 流水线告警（通知/聚合/工单三合一）")
    ap.add_argument("--batch", default=None, help="批次号（缺省=最新有 manifest 的批次）")
    ap.add_argument("--send", action="store_true", help="强制走 webhook（缺省 dry-run）")
    args = ap.parse_args()

    batch = args.batch or latest_batch()
    if not batch:
        print("[alert] 未发现任何 output_batch*/manifest.json，跳过")
        return 0
    a = assess(batch)
    print(f"[alert] batch{batch} → {a['severity']}（{a['reason']}）")
    if a["severity"] == "OK":
        return 0

    STATE_PATH.parent.mkdir(parents=True, exist_ok=True)
    state = json.loads(STATE_PATH.read_text(encoding="utf-8")) if STATE_PATH.exists() else {}
    fp = f"batch{batch}:{a['severity']}"
    do_send, count = should_notify(state, fp, a["severity"])
    STATE_PATH.write_text(json.dumps(state, ensure_ascii=False, indent=1), encoding="utf-8")
    if not do_send:
        print(f"[聚合] {fp} 静默窗口内（{QUIET_H}h），第 {count} 次出现，抑制通知")
        return 0

    upgraded = count >= ESCALATE_N or a["severity"] == "BLOCKED"
    deliver(render_markdown(a, count, upgraded), args)
    if upgraded:
        open_ticket({**a, "count": count, "ts": time.strftime("%Y-%m-%dT%H:%M:%S")})
    return 2 if a["severity"] == "BLOCKED" else 1


if __name__ == "__main__":
    sys.exit(main())
