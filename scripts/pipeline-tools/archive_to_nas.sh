#!/usr/bin/env bash
# =============================================================================
# @file scripts/pipeline-tools/archive_to_nas.sh
# @author YanYuCloudCube Team <admin@0379.email>
# @version v1.0.0
# @created 2026-09-14
# @updated 2026-09-14
# @license MIT
#
# Phase 2.1 归档通道（docs/11-第五能力衔接实施方案.md）
# 双速制归档（依据《第五能力审核论证》修正 3）：
#   - manifest 快车道：manifest.json + report/analysis（KB 级）—— 可实时同步
#   - 媒体慢车道：output_batchXX/*.mp4（百 MB 级）—— 夜间批量 rsync -z 断点续传
# 降级策略：NAS 不可达时写入 .nas_pending 待同步队列，不阻断流水线（退出码恒 0，
# 除非 --strict 模式）。待队列由 --retry-pending 在 NAS 恢复后补同步。
#
# 用法：
#   archive_to_nas.sh --batch 05                  # 快车道+慢车道全量归档
#   archive_to_nas.sh --batch 05 --manifest-only  # 仅快车道（实时场景）
#   archive_to_nas.sh --retry-pending             # 补同步历史待队列
#
# 配置（环境变量，均有默认值）：
#   YYC3_NAS_SSH   SSH 目标（user@host，Tailscale 网内），默认 yanyu@yyc3-nas
#   YYC3_NAS_BASE  NAS 归档根目录，默认 /Volume1/yyc3_hd
#   YYC3_NAS_PORT  SSH 端口，默认 22
# =============================================================================
# set -u 注意：本机 PayGuard safe_rm 拦截器会向子 bash 注入 init 文件，其顶层
# 裸引用 USERPROFILE 等未定义变量，与 set -u 冲突（仅交互链路触发）。因此这里
# 不用 set -u，改为对关键变量显式判空（生产 cron 直调 /bin/bash 无此问题）。
# =============================================================================

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)" || exit 1
REPO_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)" || exit 1
PENDING_FILE="$REPO_ROOT/.nas_pending"
LOG_DIR="$REPO_ROOT/logs"
mkdir -p "$LOG_DIR"

NAS_SSH="${YYC3_NAS_SSH:-yanyu@yyc3-nas}"
NAS_BASE="${YYC3_NAS_BASE:-/Volume1/yyc3_hd}"
NAS_PORT="${YYC3_NAS_PORT:-22}"
[ -n "$NAS_SSH" ] && [ -n "$NAS_BASE" ] || { echo "❌ NAS 配置为空"; exit 2; }
LOG="$LOG_DIR/nas_archive_$(date +%Y%m%d).log"

log()  { echo "[$(date '+%F %T')] $*" | tee -a "$LOG"; }
warn() { log "⚠️  $*"; }
ok()   { log "✅ $*"; }

# 检测 NAS 可达性（5s 超时，Tailscale 网内正常应秒级响应）
nas_reachable() {
  ssh -p "$NAS_PORT" -o ConnectTimeout=5 -o BatchMode=yes "$NAS_SSH" "true" 2>/dev/null
}

# 入队：NAS 不可达时的降级记录（去重）
enqueue() {
  local batch="$1"
  touch "$PENDING_FILE"
  grep -qx "$batch" "$PENDING_FILE" 2>/dev/null || echo "$batch" >> "$PENDING_FILE"
  warn "批次 batch$batch 已入待同步队列（$PENDING_FILE）"
}

# 归档单个批次（$1=批次号，$2=manifest-only 与否）
archive_batch() {
  local batch="$1" manifest_only="$2"
  local src="$REPO_ROOT/output_batch$batch"
  local nas_dst="$NAS_BASE/video_batch$batch"

  if [ ! -d "$src" ]; then
    warn "跳过：$src 不存在"
    return 1
  fi
  if ! nas_reachable; then
    warn "NAS 不可达（$NAS_SSH），降级入队"
    enqueue "$batch"
    return 1
  fi

  # 远端建目录（含批次目录）
  ssh -p "$NAS_PORT" "$NAS_SSH" "mkdir -p '$nas_dst'" 2>>"$LOG" || { enqueue "$batch"; return 1; }

  # 快车道：manifest + report + analysis（KB 级，实时无压力）
  # -z 压缩 + --partial 断点续传 + --timeout 防挂起（审核论证修正 3：Tailscale ~2MB/s）
  for f in "$src/manifest.json" "$REPO_ROOT/report_batch$batch.md" "$REPO_ROOT/analysis_result_batch$batch.md"; do
    [ -f "$f" ] && rsync -az --partial --timeout=60 -e "ssh -p $NAS_PORT" \
      "$f" "$NAS_SSH:$nas_dst/" 2>>"$LOG" && ok "快车道：$(basename "$f")" || warn "快车道失败：$f"
  done
  # 快车道顺带清掉待队列中该批次的快车道欠账
  [ -f "$PENDING_FILE" ] && sed -i '' "/^$batch$/d" "$PENDING_FILE" 2>/dev/null

  # 慢车道：媒体成品（--manifest-only 时跳过，留给夜间批量）
  if [ "$manifest_only" = "no" ]; then
    log "慢车道开始：$src → $nas_dst（媒体文件，夜间窗口执行）"
    if rsync -az --partial --timeout=600 -e "ssh -p $NAS_PORT" "$src/" "$NAS_SSH:$nas_dst/" 2>>"$LOG"; then
      ok "慢车道完成：batch$batch 全量归档"
    else
      warn "慢车道中断（断点已保留，重跑本脚本即续传）"
      enqueue "$batch"
      return 1
    fi
  fi
  return 0
}

main() {
  local batch="" manifest_only="no" retry="no"
  while [ $# -gt 0 ]; do
    case "$1" in
      --batch) batch="$2"; shift 2 ;;
      --manifest-only) manifest_only="yes"; shift ;;
      --retry-pending) retry="yes"; shift ;;
      --strict) STRICT="yes"; shift ;;  # NAS 失败时退出非 0（CI/编排用）
      *) echo "未知参数：$1"; exit 2 ;;
    esac
  done

  local rc=0
  if [ "$retry" = "yes" ]; then
    [ -f "$PENDING_FILE" ] || { log "无待同步队列"; exit 0; }
    log "补同步待队列：$(tr '\n' ' ' < "$PENDING_FILE")"
    for b in $(cat "$PENDING_FILE"); do archive_batch "$b" "no" || rc=1; done
  elif [ -n "$batch" ]; then
    archive_batch "$batch" "$manifest_only" || rc=1
  else
    echo "用法：$0 --batch 05 [--manifest-only] | --retry-pending"; exit 2
  fi

  # 非 strict 模式恒 0 退出（流水线钩子友好；审核论证：归档失败不阻断生产）
  [ "${STRICT:-no}" = "yes" ] && exit "$rc"
  exit 0
}

main "$@"
