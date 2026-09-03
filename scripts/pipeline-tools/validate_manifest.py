#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
@file validate_manifest.py
@author YanYuCloudCube Team <admin@0379.email>
@version v1.0.0
@created 2026-09-03
@updated 2026-09-03
@status stable
@copyright Copyright (c) 2025-2026 YYC3 Team
@license MIT


validate_manifest.py — Python 端 manifest 双端契约校验器（路线C schema 契约落地）

数据流：zod（packages/manifest-schema）→ gen-json-schema 生成 → 本脚本消费
校验对象：output_batch*/manifest.json（写端自检，可挂 pipeline_auto 步骤④ 前或 CI）

依赖：jsonschema（可选）。未安装时降级为结构快检（键存在性），不阻断。
用法：python scripts/pipeline-tools/validate_manifest.py [--all | --batch 01]
"""
import argparse
import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
SCHEMA_FILE = REPO_ROOT / "packages" / "manifest-schema" / "schema" / "manifest.schema.json"

REQUIRED_KEYS = ("batch", "started_at", "model", "records")


def load_validator():
    """jsonschema 可用则返回真校验器，否则 None（结构快检兜底）"""
    try:
        import jsonschema  # noqa: F401
    except ImportError:
        return None
    schema = json.loads(SCHEMA_FILE.read_text(encoding="utf-8"))
    # openApi3 target 生成结果兼容 Draft-07 语义；直接用 jsonschema.validate
    return lambda data: jsonschema.validate(data, schema)


def quick_check(data: dict) -> list[str]:
    errors = []
    for key in REQUIRED_KEYS:
        if key not in data:
            errors.append(f"缺少必需键: {key}")
    for i, rec in enumerate(data.get("records", [])):
        for key in ("ref_img", "seed", "status"):
            if key not in rec:
                errors.append(f"records[{i}] 缺少 {key}")
    return errors


def validate_one(mf: Path, validator) -> bool:
    try:
        data = json.loads(mf.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError) as e:
        print(f"{mf.parent.name}: ❌ JSON 解析失败 {e}")
        return False
    if validator is not None:
        try:
            validator(data)
            print(f"{mf.parent.name}: ✅ JSON Schema 校验通过")
            return True
        except Exception as e:  # jsonschema.ValidationError
            print(f"{mf.parent.name}: ❌ Schema 不符 {e}")
            return False
    errors = quick_check(data)
    if errors:
        print(f"{mf.parent.name}: ⚠️ 结构快检失败 {'; '.join(errors)}")
        return False
    print(f"{mf.parent.name}: ✅ 结构快检通过（安装 jsonschema 可获完整校验）")
    return True


def main():
    parser = argparse.ArgumentParser(description="manifest 双端契约校验")
    parser.add_argument("--batch", help="指定批次（如 01）")
    parser.add_argument("--all", action="store_true", help="校验全部批次")
    args = parser.parse_args()

    validator = load_validator()
    targets = (
        [REPO_ROOT / f"output_batch{args.batch}" / "manifest.json"]
        if args.batch
        else sorted(REPO_ROOT.glob("output_batch*/manifest.json"))
    )
    targets = [t for t in targets if t.exists()]
    if not targets:
        print("未找到 manifest.json")
        return 1

    ok = all(validate_one(t, validator) for t in targets)
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
