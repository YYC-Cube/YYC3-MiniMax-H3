#!/usr/bin/env bash
# g4t2_watch_and_retry_batch1002.sh - 一次性守望定时器（09-28 现场决策落地）
# 背景：Drama 副本的 g4t2 preview 批（22:21 起，nice）独占 MPS；batch1002 昨夜
# 22:23 被外部 SIGTERM（优雅终止首战：FAILED/SKIPPED/ended_at 全收敛）。
# 决策：g4t2 先跑，batch1002 视窗口余量自动续跑或顺延。
# 设计：
#   - 一次性：首次触发即自解除 crontab 行（防次日 00:30 与 batch1003 撞车）
#   - 窗口按「待重跑 seed 数 × 4.5h + 0.5h」动态判定（batch1002 现状 2 seed ≈ 需 9.5h）
#   - 待重跑数从 manifest 实时读取；已被人工处理（无 FAILED/SKIPPED）则不动作
set -u
cd /Users/yanyu/YYC-Cube/YYC3-MiniMax-H3
LOG=logs/g4t2_watch_20260929.log
PY=/opt/miniconda3/envs/h3-m4/bin/python

# 自解除：grep -v 删自身行（幂等；触发即解除，无论走哪个分支）
crontab -l 2>/dev/null | grep -v "g4t2_watch_and_retry" | crontab -

{
  echo "=== $(date '+%F %T') 守望触发（一次性，已自解除）==="
  if pgrep -f "batch_ref2va_nf4.py --batch g4t2" >/dev/null; then
    echo "g4t2 仍在生成 → batch1002 顺延。手动续跑：H3_BATCH=1002 bash scripts/pipeline-tools/nightly_run.sh"
    exit 0
  fi
  echo "g4t2 已结束，检查 batch1002 待重跑量…"
  SEEDS_NEEDED=$("$PY" - <<'EOF'
import json
try:
    m = json.load(open("output/manifests/batch1002/manifest.json"))
    recs = m.get("records", [])
    print(sum(1 for r in recs if r.get("status") in ("FAILED", "SKIPPED", "READ_FAILED")))
except Exception:
    print(-1)
EOF
) || SEEDS_NEEDED=-1
  if [ "$SEEDS_NEEDED" -le 0 ]; then
    echo "batch1002 无待重跑任务（读数 $SEEDS_NEEDED，可能已人工处理）→ 不动作"
    exit 0
  fi
  NOW=$(date +%s)
  DEADLINE=$(date -j -f "%Y-%m-%d %H:%M" "$(date '+%Y-%m-%d') 08:00" "+%s")
  LEFT_H=$(((DEADLINE - NOW) / 3600))
  NEED_H=$("$SEEDS_NEEDED" | awk '{printf "%d", $1 * 4.5 + 0.5}')
  echo "待重跑 ${SEEDS_NEEDED} seed ≈ 需 ${NEED_H}h；距 08:00 窗口截止剩 ${LEFT_H}h"
  if [ "$LEFT_H" -ge "$NEED_H" ]; then
    echo "窗口足够 → 自动重跑 batch1002（FAILED/SKIPPED 自动续跑）"
    H3_BATCH=1002 bash scripts/pipeline-tools/nightly_run.sh >> logs/cron_nightly.log 2>&1
    echo "重跑收尾 exit=$?"
  else
    echo "窗口不足 → 顺延。手动续跑：H3_BATCH=1002 bash scripts/pipeline-tools/nightly_run.sh（明晚 cron 自动开 batch1003）"
  fi
} >> "$LOG" 2>&1
