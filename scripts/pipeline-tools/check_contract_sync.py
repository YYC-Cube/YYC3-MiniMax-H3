#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
@file scripts/pipeline-tools/check_contract_sync.py
@author YanYuCloudCube Team <admin@0379.email>
@version v1.0.0
@created 2026-09-26

batches.json 双端契约一致性校验（docs/16 P0 契约包配套 CI 门禁）
- TS 端真源：packages/manifest-schema/src/batches.ts（BATCH_ENVELOPE_FIELDS / BATCH_UNIT_FIELDS）
- Python 端真源：本脚本内 WRITE_END_* 清单（镜像 scripts/pipeline-tools/export_dashboard_data.py
  的 payload 构造与 build_batch() 返回；修改写端字段时必须同步本清单）
- 判定：两侧字段集合必须完全一致（差集双向报告），不一致 exit 1
用法：python3 scripts/pipeline-tools/check_contract_sync.py
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
TS_FILE = REPO / "packages/manifest-schema/src/batches.ts"

# Python 写端字段清单（与 export_dashboard_data.py 逐字段对齐 —— 改字段必改此处）
WRITE_END_ENVELOPE = ["schema_version", "generated_at", "score_scale", "batches", "top10"]
WRITE_END_BATCH_UNIT = [
    "id", "time", "ended", "model", "pipeline", "refImages", "seeds",
    "success", "failed", "skipped", "avgScore", "maxScore", "status",
    "videos", "defects", "params", "durationMin",
]


def ts_fields(const_name: str) -> list[str]:
    src = TS_FILE.read_text(encoding="utf-8")
    m = re.search(const_name + r"\s*=\s*\[(.*?)\]", src, re.S)
    if not m:
        print(f"FAIL  TS 端未找到 {const_name}（{TS_FILE}）")
        sys.exit(2)
    return re.findall(r'"([^"]+)"', m.group(1))


def check(label: str, ts: list[str], py: list[str]) -> bool:
    ts_set, py_set = set(ts), set(py)
    if ts_set == py_set:
        print(f"OK    {label}: {len(ts_set)} 字段一致")
        return True
    print(f"FAIL  {label} 不一致：")
    print(f"      TS 多/缺: {sorted(ts_set - py_set) or '无'} | Python 多/缺: {sorted(py_set - ts_set) or '无'}")
    return False


def main() -> int:
    ok = check("envelope", ts_fields("BATCH_ENVELOPE_FIELDS"), WRITE_END_ENVELOPE)
    ok = check("batch 单元", ts_fields("BATCH_UNIT_FIELDS"), WRITE_END_BATCH_UNIT) and ok
    print("PASS" if ok else "FAIL", "- batches 契约双端一致性")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
