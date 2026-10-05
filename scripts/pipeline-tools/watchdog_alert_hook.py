#!/usr/bin/env python3
"""
watchdog_alert_hook.py — 看门狗告警钩子（docs/21 §五 · 告警纪律对齐件）

告警纪律（project_memory 工程约定）：指纹 + 6h 静默窗口 + 连续 3 次升级 @提醒。
本钩子由 launchd plist 链式调用（看门狗退出后携 --last-exit 运行），职责：

  1. 退出码分级：exit 1（本地探活失败）计入连续失败；exit 2（线上 TTFB 抖动）
     为观测性告警——仅记录不升级（避免白天网络抖动轰炸）；exit 0 → 恢复清零
  2. 升级判定：同指纹连续失败 ≥3 次 → L1 提醒；此后每 +3 升一级（L2/L3 封顶）
  3. 静默窗口：同指纹 6h 内已通知则跳过（计数继续累计，窗口过后按当前 level 通知）
  4. 恢复通知：失败→成功 转换发一条 recovery（不受静默限制，验证告警链路活着）

通知渠道（全部可选叠加，缺省仅落盘）：
  - macOS 通知中心（osascript display notification）
  - H3_ALERT_WEBHOOK（env，POST JSON；飞书/Slack 网关自备，密钥不入库）
  - logs/watchdog_alerts.jsonl（审计流，NAS 可同步）

状态文件：logs/.watchdog_alert_state.json（指纹→{consecutive, last_notify, level}）

用法（plist 链式）：
  python3 watchdog_alert_hook.py --last-exit 1 --quiet
退出码：0 正常（含静默跳过）/ 1 钩子自身异常（不影响看门狗语义）
"""
import json
import os
import subprocess
import sys
import time
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
WATCH_JSONL = REPO_ROOT / "logs" / "console_watch.jsonl"
ALERT_JSONL = REPO_ROOT / "logs" / "watchdog_alerts.jsonl"
STATE_FILE = REPO_ROOT / "logs" / ".watchdog_alert_state.json"

ESCALATE_AFTER = 3          # 连续失败 N 次后首次通知（告警纪律「连续 3 次」）
SILENCE_WINDOW_S = 6 * 3600  # 同指纹静默窗口 6h（告警纪律）
MAX_LEVEL = 3               # L1 提醒 / L2 升级 / L3 严重（封顶）
WEBHOOK = os.environ.get("H3_ALERT_WEBHOOK", "").strip()
CONSOLE_URL = os.environ.get("CONSOLE_URL", "http://127.0.0.1:3030")
LANDING_URL = "https://h3.yyc3.top"


def ts() -> str:
    return datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")


def load_state() -> dict:
    try:
        return json.loads(STATE_FILE.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}


def save_state(state: dict) -> None:
    STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
    STATE_FILE.write_text(json.dumps(state, ensure_ascii=False, indent=1), encoding="utf-8")


def last_record() -> dict:
    try:
        lines = WATCH_JSONL.read_text(encoding="utf-8").strip().splitlines()
        return json.loads(lines[-1]) if lines else {}
    except (OSError, json.JSONDecodeError, IndexError):
        return {}


def emit_alert(fp: str, level: int, consecutive: int, kind: str, detail: str) -> None:
    """通知分发：osascript + webhook + 审计落盘（三渠道独立降级）"""
    event = {"ts": ts(), "kind": kind, "fingerprint": fp, "level": level,
             "consecutive": consecutive, "detail": detail}
    try:
        ALERT_JSONL.parent.mkdir(parents=True, exist_ok=True)
        with ALERT_JSONL.open("a", encoding="utf-8") as f:
            f.write(json.dumps(event, ensure_ascii=False) + "\n")
    except OSError:
        pass

    if kind == "recovery":
        title, body = "✅ 看门狗恢复", fp
    else:
        title = f"🔔 看门狗 L{level} {'严重' if level >= 3 else '升级' if level >= 2 else '提醒'}"
        body = f"{fp} · 连续失败 {consecutive} 次"
    try:
        subprocess.run(
            ["osascript", "-e",
             f'display notification "{body}" with title "{title}" sound name "Ping"'],
            timeout=5, capture_output=True)
    except Exception:
        pass  # 通知中心不可用不阻断（headless/SSH 会话常态）

    if WEBHOOK:
        try:
            req = urllib.request.Request(
                WEBHOOK, data=json.dumps(event, ensure_ascii=False).encode("utf-8"),
                headers={"Content-Type": "application/json"})
            urllib.request.urlopen(req, timeout=5)
        except Exception:
            pass  # webhook 失败不影响本地渠道（审计流已有留痕）

    if "--quiet" not in sys.argv:
        print(json.dumps(event, ensure_ascii=False))


def main() -> int:
    try:
        args = sys.argv[1:]
        last_exit = int(args[args.index("--last-exit") + 1]) if "--last-exit" in args else 0
    except (ValueError, IndexError):
        last_exit = 0

    rec = last_record()
    mode = rec.get("mode", "landing-only")
    # 指纹：模式 + 失败维度（landing-only 指向线上站点；full 指向本机 console）
    fp = f"{mode}:{LANDING_URL if mode == 'landing-only' else CONSOLE_URL}"

    state = load_state()
    entry = state.get(fp, {"consecutive": 0, "last_notify_ts": "", "level": 0})

    if last_exit == 0:
        if entry["consecutive"] > 0:
            emit_alert(fp, 0, 0, "recovery", f"探活恢复（此前连续失败 {entry['consecutive']} 次）")
        entry = {"consecutive": 0, "last_notify_ts": "", "level": 0}
        state[fp] = entry
        save_state(state)
        return 0

    if last_exit == 2:
        # 观测性告警（线上抖动）：仅刷新状态不升级不通知——白天网络抖动防轰炸
        state[fp] = entry
        save_state(state)
        return 0

    # exit 1：本地探活失败 → 连续计数 + 升级判定
    entry["consecutive"] += 1
    now = time.time()
    notified_recently = False
    if entry["last_notify_ts"]:
        try:
            notified_recently = (now - datetime.fromisoformat(entry["last_notify_ts"]).timestamp()
                                 ) < SILENCE_WINDOW_S
        except ValueError:
            notified_recently = False

    # 升级公式：每满 ESCALATE_AFTER 次升一级（L1@3 / L2@6 / L3@9 封顶）——
    # 4 次时 new_level 仍为 1，与 entry.level 相同 → 落入 6h 静默（防每轮轰炸）
    new_level = min(MAX_LEVEL, entry["consecutive"] // ESCALATE_AFTER) \
        if entry["consecutive"] >= ESCALATE_AFTER else 0

    should_notify = (entry["consecutive"] >= ESCALATE_AFTER
                     and (not notified_recently or new_level > entry["level"]))

    detail = f"最近探测：{json.dumps(rec, ensure_ascii=False)[:200]}"
    if should_notify:
        emit_alert(fp, new_level, entry["consecutive"], "escalate", detail)
        entry["last_notify_ts"] = ts()
        entry["level"] = new_level
    state[fp] = entry
    save_state(state)
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception as e:  # 钩子自身异常不放大故障（看门狗语义不受影响）
        print(f"❌ [alert-hook] {e}", file=sys.stderr)
        sys.exit(1)
