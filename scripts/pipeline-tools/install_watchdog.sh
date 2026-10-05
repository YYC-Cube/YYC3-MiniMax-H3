#!/usr/bin/env bash
# =============================================================================
# @file scripts/pipeline-tools/install_watchdog.sh
# @author YanYuCloudCube Team <admin@0379.email>
# @version v1.0.0
# @created 2026-10-05
# @updated 2026-10-05
# @license MIT
#
# 看门狗一键安装器（docs/21 §二 · B4 收口件）
#
# 背景：cron 挂载在受限执行环境（沙箱/CI）下会被 macOS setuid crontab 特权
# 写路径阻断（读取正常、写入挂死）。launchd 用户域（gui/$UID）无此依赖——
# 本脚本以 launchd 为首选通道，cron 作为备选手动方案（docs/17 §5.3）。
#
# 用法：
#   bash scripts/pipeline-tools/install_watchdog.sh               # 安装/更新（幂等）+ 自检 + 立即试跑
#   bash scripts/pipeline-tools/install_watchdog.sh --status      # 查看挂载状态
#   bash scripts/pipeline-tools/install_watchdog.sh --uninstall   # 回滚（bootout + 删 plist）
#
# 产物：~/Library/LaunchAgents/com.yyc3.console-watch.plist（StartInterval 600s
#       ≙ cron */10；RunAtLoad 安装即首跑；日志 logs/console_watch_launchd.log）
# 退出码：0 成功 / 1 安装或自检失败（详情见 stderr）
#
# 可回滚性：--uninstall 完整移除（plist + launchd 注册），不留系统残留。
# =============================================================================
set -u  # 不用 set -e：launchctl 老新语法差异需手动 fallback（同 nightly_run.sh 头注惯例）

export PATH="/opt/homebrew/bin:/opt/homebrew/sbin:/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin"

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)" || exit 1
REPO_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)" || exit 1
LABEL="com.yyc3.console-watch"
PLIST="$HOME/Library/LaunchAgents/${LABEL}.plist"
LOG_FILE="$REPO_ROOT/logs/console_watch_launchd.log"
PYTHON="/opt/miniconda3/envs/h3-m4/bin/python"
WATCH_SCRIPT="$SCRIPT_DIR/console_health_check.py"
INTERVAL_S="${H3_WATCH_INTERVAL:-600}"   # 默认 10 分钟（≙ cron */10，docs/17 §5.3）
UID_DIR="$(id -u)"

die() { echo "❌ [watchdog-install] $*" >&2; exit 1; }
info() { echo "[watchdog-install] $*"; }

[ -x "$PYTHON" ] || die "Python 不可用：$PYTHON（H3_PYTHON 环境口径见 docs/01）"
[ -f "$WATCH_SCRIPT" ] || die "看门狗脚本不存在：$WATCH_SCRIPT"
mkdir -p "$REPO_ROOT/logs" "$HOME/Library/LaunchAgents"

is_loaded() {
  launchctl print "gui/${UID_DIR}/${LABEL}" >/dev/null 2>&1 \
    || launchctl list "$LABEL" >/dev/null 2>&1
}

write_plist() {
  local hook_script="$SCRIPT_DIR/watchdog_alert_hook.py"
  [ -f "$hook_script" ] || hook_script=""
  # 链式调用（docs/21 §五）：探活退出后携退出码跑告警钩子（exit 1 连续 3 次→升级通知，
  # 对齐告警纪律：指纹+6h 静默+连续 3 次）；钩子缺失时退化为纯探活（兼容旧布局）
  local chain="\"$PYTHON\" \"$WATCH_SCRIPT\" --landing-only --quiet; rc=\$?;"
  if [ -n "$hook_script" ]; then
    chain+=" \"$PYTHON\" \"$hook_script\" --last-exit \"\$rc\" --quiet"
  fi
  cat > "$PLIST" <<PLISTEOF
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
  <key>Label</key><string>${LABEL}</string>
  <key>ProgramArguments</key>
  <array>
    <string>/bin/bash</string>
    <string>-c</string>
    <string>${chain}</string>
  </array>
  <key>StartInterval</key><integer>${INTERVAL_S}</integer>
  <key>RunAtLoad</key><true/>
  <key>ProcessType</key><string>Background</string>
  <key>LowPriorityIO</key><true/>
  <key>StandardOutPath</key><string>${LOG_FILE}</string>
  <key>StandardErrorPath</key><string>${LOG_FILE}</string>
  <key>EnvironmentVariables</key>
  <dict>
    <key>PATH</key><string>/opt/homebrew/bin:/opt/homebrew/sbin:/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin</string>
  </dict>
</dict>
</plist>
PLISTEOF
}

load_service() {
  # 新语法优先（bootstrap），旧 macOS 回退 load -w；幂等：先卸后装
  launchctl bootout "gui/${UID_DIR}/${LABEL}" >/dev/null 2>&1
  launchctl unload "$PLIST" >/dev/null 2>&1
  if launchctl bootstrap "gui/${UID_DIR}" "$PLIST" >/dev/null 2>&1; then
    return 0
  fi
  launchctl load -w "$PLIST" >/dev/null 2>&1
}

cmd_install() {
  # —— 前置自检：手动跑一次看门狗（语法/网络环境先验证，避免挂起一个坏任务）——
  # 退出码分级（console_health_check 契约）：0 全过 / 1 本地探活失败（阻断）/
  # 2 仅线上 TTFB 抖动超标（观测性告警——持续观测抖动正是挂载目的，放行并提示）
  info "前置自检：手动试跑 console_health_check --landing-only …"
  rc=0
  "$PYTHON" "$WATCH_SCRIPT" --landing-only --quiet || rc=$?
  if [ "$rc" = "1" ]; then
    die "试跑本地探活失败（exit=1）——先解决探活环境再挂载（详情见 stderr）"
  elif [ "$rc" = "2" ]; then
    info "⚠ 线上 TTFB 抖动超标（exit=2，观测性告警）——不阻断挂载，挂载后持续观测"
  elif [ "$rc" != "0" ]; then
    die "试跑异常退出（exit=$rc）"
  fi

  write_plist
  chmod 644 "$PLIST"
  load_service || die "launchd 注册失败（bootstrap 与 load 均未成功）"
  is_loaded || die "注册后自检失败：launchctl 查无 ${LABEL}"
  sleep 2   # RunAtLoad 首跑缓冲

  # —— 挂载后实证：launchd 首跑应追加 JSONL ——
  local before after
  before="$(wc -l < "$REPO_ROOT/logs/console_watch.jsonl" 2>/dev/null || echo 0)"
  launchctl kickstart -k "gui/${UID_DIR}/${LABEL}" >/dev/null 2>&1 || true
  sleep 6   # 探测含 5×TTFB 采样（≥2s）+ 0.3s 间隔
  after="$(wc -l < "$REPO_ROOT/logs/console_watch.jsonl" 2>/dev/null || echo 0)"

  echo "✅ 看门狗已挂载（launchd · gui/${UID_DIR}）"
  echo "   plist:    $PLIST"
  echo "   周期:     每 ${INTERVAL_S}s（kickstart 试跑 JSONL ${before}→${after} 行）"
  echo "   日志:     $LOG_FILE"
  echo "   回滚:     bash $SCRIPT_DIR/install_watchdog.sh --uninstall"
  [ "$after" -gt "$before" ] || info "⚠ kickstart 后 JSONL 未增长（首跑可能仍在采样，稍后 tail 复核）"
  exit 0
}

cmd_uninstall() {
  launchctl bootout "gui/${UID_DIR}/${LABEL}" >/dev/null 2>&1
  launchctl unload "$PLIST" >/dev/null 2>&1
  rm -f "$PLIST"
  if is_loaded; then die "卸载后仍查到 ${LABEL}"; fi
  [ -f "$PLIST" ] && die "plist 仍存在：$PLIST"
  echo "✅ 看门狗已卸载（plist 已删 + launchd 已注销）；历史探测数据保留于 logs/console_watch.jsonl"
  exit 0
}

cmd_status() {
  if is_loaded; then
    echo "✅ ${LABEL} 已挂载"
    launchctl print "gui/${UID_DIR}/${LABEL}" 2>/dev/null | grep -E "state|runs|last exit" | head -5
    echo "   plist: $PLIST"
    echo "   最近探测：$(tail -1 "$REPO_ROOT/logs/console_watch.jsonl" 2>/dev/null || echo '（无记录）')"
  else
    echo "⛔ ${LABEL} 未挂载（$PLIST $([ -f "$PLIST" ] && echo 存在但未注册 || echo 不存在)）"
    exit 1
  fi
}

case "${1:-install}" in
  install)    cmd_install ;;
  --status)   cmd_status ;;
  --uninstall) cmd_uninstall ;;
  *) echo "用法: $0 [install|--status|--uninstall]" >&2; exit 1 ;;
esac
