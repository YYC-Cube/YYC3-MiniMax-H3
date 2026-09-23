#!/usr/bin/env bash
# =============================================================================
# @file scripts/pipeline-tools/nightly_run.sh
# @author YanYuCloudCube Team <admin@0379.email>
# @version v1.1.0
# @created 2026-09-14
# @updated 2026-09-18
# @license MIT
#
# Phase 2.2 夜间批量编排（docs/11-第五能力衔接实施方案.md）
# 依据《第五能力审核论证》修正 1：Mac=主开发机，批量任务必须走夜间窗口
#（22:00-08:00 硬约束），白天仅允许单条/少帧冒烟。
#
# 职责：夜间全链路「生成→评分→分析→归档→次晨报告」
#   ① pipeline_auto.py --auto --batch N   全自动流水线（--auto 跳过人工暂停）
#   ② archive_to_nas.sh  --batch N        双速制 NAS 归档（manifest+媒体）
#   ③ archive_to_nas.sh  --retry-pending  补同步历史欠账（NAS 恢复后自愈）
#   ④ 次晨报告：logs/nightly_YYYYMMDD.md（摘要 + 归档状态）
#
# 安装（crontab -e，注意 % 在 cron 中需转义）：
#   0 22 * * * /path/to/YYC3-MiniMax-H3/scripts/pipeline-tools/nightly_run.sh >> /path/to/YYC3-MiniMax-H3/logs/cron_nightly.log 2>&1
#
# 环境变量（可选）：
#   H3_BATCH     指定批次号（默认自动递增）
#   H3_NIGHTLY_SKIP_GENERATE=1  跳过生成，仅做归档+补同步（调试用）
#   H3_PYTHON    覆盖 Python 解释器路径（默认 h3-m4 conda env）
#
# 2026-09-18 加固（两起夜间事故修复）：
#   ① cron 上下文 python3=/usr/bin/python3 撞 Xcode license → exit 69，
#      09-16 夜间阶段①/④全灭 → 显式锚定 h3-m4 env python
#   ② 09-17 B 臂电池 1% 触发 Low Power Sleep 休眠 1h40m，生成中途冻结
#      （pmset 实证 22:48 休眠 → 00:28 接电唤醒续跑）→ AC 电源守卫 + caffeinate
# =============================================================================
# set -u 注意：本机 PayGuard safe_rm 拦截器与 set -u 冲突（见 archive_to_nas.sh
# 头注），故不用 set -u；关键路径变量在使用点显式判空。
# =============================================================================
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)" || exit 1
REPO_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)" || exit 1
cd "$REPO_ROOT" || exit 1

TODAY="$(date +%Y%m%d)"
REPORT="$REPO_ROOT/logs/nightly_$TODAY.md"
NIGHT_START="22"   # 夜间窗口起始小时（硬约束，见审核论证修正 1）
NIGHT_END="08"     # 窗口结束小时

mkdir -p "$REPO_ROOT/logs"

# —— caffeinate 防睡眠：整个夜间批量期间阻止系统 idle sleep（一次性 re-exec）——
if [ "${H3_CAFFEINATE:-0}" != "1" ] && command -v caffeinate >/dev/null 2>&1; then
  exec env H3_CAFFEINATE=1 caffeinate -i "$0" "$@"
fi

# —— Python 锚定：cron 里 python3 是 /usr/bin/python3（Xcode license 未同意 → exit 69）——
PYTHON="${H3_PYTHON:-/opt/miniconda3/envs/h3-m4/bin/python}"
if [ ! -x "$PYTHON" ]; then
  echo "[$(date '+%F %T')] ❌ Python 不可用：$PYTHON（可用 H3_PYTHON 覆盖）"
  exit 1
fi

# —— AC 电源守卫：电池跑批量必触 Low Power Sleep 冻结生成（09-17 实证）——
# H3_FORCE=1 与窗口守卫共用逃生阀
power_src="$(pmset -g batt 2>/dev/null | head -1)"
if [ "${H3_FORCE:-0}" != "1" ] && ! echo "$power_src" | grep -q "AC Power"; then
  echo "[$(date '+%F %T')] ⛔ 未接 AC 电源（${power_src:-未知}），拒绝夜间批量——"
  echo "            电池耗尽触发休眠会冻结生成（09-17 batch91 seed42 实证休眠 1h40m）。接电后自动恢复。"
  exit 1
fi

# —— 夜间窗口守卫：白天地手动触发直接拒绝（防止与开发争内存）——
# H3_FORCE=1 逃生阀：显式强制执行（调试/编排方自担窗口责任），正常生产勿用
hour="$(date +%H)"
if [ "${H3_FORCE:-0}" != "1" ] && [ "$hour" -ge "$NIGHT_END" ] && [ "$hour" -lt "$NIGHT_START" ]; then
  echo "[$(date '+%F %T')] ⛔ 非夜间窗口（${NIGHT_START}:00-${NIGHT_END}:00 之外），拒绝批量任务（审核论证修正 1 硬约束）。"
  echo "            冒烟调试请用：python scripts/pipeline-tools/pipeline_auto.py --dry-run"
  exit 1
fi

{
  echo "# 🌙 夜间批量报告 batch${H3_BATCH:-auto}（$TODAY）"
  echo ""
  echo "| 阶段 | 开始时间 | 结果 |"
  echo "| ---- | -------- | ---- |"
} > "$REPORT"

stage() {  # stage <名称> <命令...>
  local name="$1"; shift
  local t0 rc
  t0="$(date '+%T')"
  echo "[$(date '+%F %T')] ▶ $name" >> "$REPORT"
  if "$@" >> "$REPORT.raw" 2>&1; then rc="✅ 成功"; else rc="❌ 失败($?)"; fi
  echo "| $name | $t0 | $rc |" >> "$REPORT"
  echo "[$(date '+%F %T')] $name → $rc"
}

BATCH_ARGS=()
[ -n "${H3_BATCH:-}" ] && BATCH_ARGS=(--batch "$H3_BATCH")

if [ "${H3_NIGHTLY_SKIP_GENERATE:-0}" != "1" ]; then
  stage "① 全自动流水线（生成→评分→分析→Seed）" \
    "$PYTHON" scripts/pipeline-tools/pipeline_auto.py --auto "${BATCH_ARGS[@]+"${BATCH_ARGS[@]}"}"
fi

# ② 归档本批次（批次号取 pipeline 产出的最新 report；skip 模式则全量扫描）
if [ -n "${H3_BATCH:-}" ]; then
  stage "② NAS 双速归档 batch$H3_BATCH" bash "$SCRIPT_DIR/archive_to_nas.sh" --batch "$H3_BATCH" --strict
else
  LATEST_B="$(ls -t report_batch*.md 2>/dev/null | head -1 | sed -E 's/report_batch([0-9]+)\.md/\1/')"
  [ -n "$LATEST_B" ] && stage "② NAS 双速归档 batch$LATEST_B" \
    bash "$SCRIPT_DIR/archive_to_nas.sh" --batch "$LATEST_B" --strict
fi

# ③ 补同步历史欠账（NAS 恢复后自愈）
stage "③ 待队列补同步" bash "$SCRIPT_DIR/archive_to_nas.sh" --retry-pending --strict

# 面板数据桥兜底刷新（manifest 可能被归档钩子更新过）
stage "④ 面板数据刷新" "$PYTHON" scripts/pipeline-tools/export_dashboard_data.py

# 收尾：raw 日志并入报告（2026-09-24 修复：原 && 链仅末命令重定向，raw 漏入 stdout/cron 日志）
if [ -f "$REPORT.raw" ]; then
  {
    echo ""
    echo "<details><summary>完整日志</summary>"
    echo ""
    echo '```'
    cat "$REPORT.raw"
    echo '```'
    echo "</details>"
  } >> "$REPORT"
  rm -f "$REPORT.raw"
fi
echo "" >> "$REPORT"
echo "生成时间：$(date '+%F %T') ｜ 报告：$REPORT" >> "$REPORT"

echo "[$(date '+%F %T')] 🌙 夜间批量完成，报告：$REPORT"
exit 0
