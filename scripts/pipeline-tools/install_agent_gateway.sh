#!/usr/bin/env bash
# =============================================================================
# @file scripts/pipeline-tools/install_agent_gateway.sh
# @author YanYuCloudCube Team <admin@0379.email>
# @version v1.0.0
# @created 2026-10-05
# @updated 2026-10-05
# @license MIT
#
# agent 网关常驻安装器（终审遗留 P3-②可选能力件 · docs/17 §2.4）
#
# 背景：agent 网关（uvicorn :8300）默认会话式启动（B2/漫剧会话时手动拉起），
# M4 资源优先生成负载。本脚本把「7×24 常驻」沉淀为一条命令的可选能力——
# 默认不激活（脚本存在即能力，需显式执行）；uvicorn 空载驻留约 50-80MB RSS。
#
# 用法：
#   bash scripts/pipeline-tools/install_agent_gateway.sh               # 常驻安装（launchd KeepAlive）
#   bash scripts/pipeline-tools/install_agent_gateway.sh --status      # 状态
#   bash scripts/pipeline-tools/install_agent_gateway.sh --uninstall   # 回滚（恢复会话式）
#
# 密钥：读 .secrets/agent_claim.env 的 AGENT_CLAIM_SECRET（不存在则警告后
#       以无密钥模式启动——网关健康但 claim 签发 fail-closed，与手动行为一致）
# 退出码：0 成功 / 1 失败
# =============================================================================
set -u
export PATH="/opt/homebrew/bin:/opt/homebrew/sbin:/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin"

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)" || exit 1
REPO_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)" || exit 1
LABEL="com.yyc3.agent-gateway"
PLIST="$HOME/Library/LaunchAgents/${LABEL}.plist"
LOG_FILE="$REPO_ROOT/logs/agent_gateway_launchd.log"
PYTHON="/opt/miniconda3/envs/h3-m4/bin/python"
UID_DIR="$(id -u)"
SECRET_FILE="$REPO_ROOT/.secrets/agent_claim.env"

die() { echo "❌ [gateway-install] $*" >&2; exit 1; }
info() { echo "[gateway-install] $*"; }

[ -x "$PYTHON" ] || die "Python 不可用：$PYTHON"
mkdir -p "$REPO_ROOT/logs" "$HOME/Library/LaunchAgents"

is_loaded() {
  launchctl print "gui/${UID_DIR}/${LABEL}" >/dev/null 2>&1 \
    || launchctl list "$LABEL" >/dev/null 2>&1
}

secret_env() {
  if [ -f "$SECRET_FILE" ]; then
    info "密钥：${SECRET_FILE}（claim 可签发）"
    grep -E "^AGENT_CLAIM_SECRET=" "$SECRET_FILE" | head -1
  else
    info "⚠ 未找到 ${SECRET_FILE}——无密钥模式启动（写操作将 fail-closed，与手动行为一致）"
    echo ""
  fi
}

cmd_install() {
  local claim_env; claim_env="$(secret_env)"
  local claim_arg=""
  [[ "$claim_env" == AGENT_CLAIM_SECRET=* ]] && claim_arg="<string>${claim_env#AGENT_CLAIM_SECRET=}</string>"

  cat > "$PLIST" <<PLISTEOF
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
  <key>Label</key><string>${LABEL}</string>
  <key>WorkingDirectory</key><string>${REPO_ROOT}</string>
  <key>ProgramArguments</key>
  <array>
    <string>${PYTHON}</string>
    <string>-m</string><string>uvicorn</string>
    <string>agent.h3_agent.gateway:app</string>
    <string>--host</string><string>127.0.0.1</string>
    <string>--port</string><string>8300</string>
  </array>
  <key>RunAtLoad</key><true/>
  <key>KeepAlive</key><true/>
  <key>ThrottleInterval</key><integer>10</integer>
  <key>ProcessType</key><string>Background</string>
  <key>StandardOutPath</key><string>${LOG_FILE}</string>
  <key>StandardErrorPath</key><string>${LOG_FILE}</string>
  <key>EnvironmentVariables</key>
  <dict>
    <key>PATH</key><string>/opt/homebrew/bin:/opt/homebrew/sbin:/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin</string>
    ${claim_arg:+<key>AGENT_CLAIM_SECRET</key>${claim_arg}}
  </dict>
</dict>
</plist>
PLISTEOF
  chmod 644 "$PLIST"
  # 密钥防泄漏：plist 属主可读即可（默认 644 含组/他读——收敛为 600）
  chmod 600 "$PLIST" 2>/dev/null

  launchctl bootout "gui/${UID_DIR}/${LABEL}" >/dev/null 2>&1
  launchctl unload "$PLIST" >/dev/null 2>&1
  launchctl bootstrap "gui/${UID_DIR}" "$PLIST" >/dev/null 2>&1 \
    || launchctl load -w "$PLIST" >/dev/null 2>&1 \
    || die "launchd 注册失败"
  is_loaded || die "注册后自检失败"

  sleep 5  # launchd 冷启 + agent 模块导入链实测约 4-5s（11:50 实测：3s 时 healthz 未就绪/6s 就绪）
  if curl -s -m 3 http://127.0.0.1:8300/api/healthz | grep -q '"status":"ok"'; then
    echo "✅ agent 网关已常驻（launchd KeepAlive · gui/${UID_DIR}）"
    echo "   健康检查：curl http://127.0.0.1:8300/api/healthz"
    echo "   日志：    $LOG_FILE"
    echo "   回滚：    bash $0 --uninstall（恢复会话式）"
  else
    info "⚠ 网关进程已注册但 healthz 未就绪（模型无关，FastAPI 秒级；查 ${LOG_FILE}）"
  fi
  exit 0
}

cmd_uninstall() {
  launchctl bootout "gui/${UID_DIR}/${LABEL}" >/dev/null 2>&1
  launchctl unload "$PLIST" >/dev/null 2>&1
  rm -f "$PLIST"
  is_loaded && die "卸载后仍查到 ${LABEL}"
  echo "✅ agent 网关常驻已移除（恢复会话式：漫剧会话时手动 uvicorn）"
  exit 0
}

cmd_status() {
  if is_loaded; then
    echo "✅ ${LABEL} 常驻中"
    launchctl print "gui/${UID_DIR}/${LABEL}" 2>/dev/null | grep -E "state|runs|last exit" | head -4
    curl -s -m 3 http://127.0.0.1:8300/api/healthz && echo ""
  else
    echo "⛔ ${LABEL} 未常驻（会话式默认态）"
    exit 1
  fi
}

case "${1:-install}" in
  install)     cmd_install ;;
  --status)    cmd_status ;;
  --uninstall) cmd_uninstall ;;
  *) echo "用法: $0 [install|--status|--uninstall]" >&2; exit 1 ;;
esac
