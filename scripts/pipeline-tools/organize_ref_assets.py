#!/usr/bin/env python3
"""
organize_ref_assets.py — Ref 资产库结构化迁移（docs/18 §四 P0-2）

作用：ref_images/ 顶层散图 → {characters,scenes,props}/ 三类目录，并生成/合并
     ref_images/assets.json 清单（契约：packages/manifest-schema/src/assets.ts）。

规则：
  · 顶层散图默认归 characters/（当前仓库 Ref 均为人物参考图；--kind 可指定）
  · 已在三类子目录内的文件不动；assets.json 已有条目按文件存在性校验合并（不删条目）
  · 幂等：重复执行零变更；默认 dry-run 只打印计划，--apply 才落盘

用法：
  python3 scripts/pipeline-tools/organize_ref_assets.py            # dry-run
  python3 scripts/pipeline-tools/organize_ref_assets.py --apply    # 执行迁移+写清单
"""
import argparse
import json
import shutil
import sys
from datetime import datetime
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
REF_DIR = REPO / "ref_images"
MANIFEST_FILE = REF_DIR / "assets.json"
KINDS = ("characters", "scenes", "props")
IMG_EXT = {".png", ".jpg", ".jpeg", ".webp"}
SCHEMA_VERSION = 1


def slugify(name: str) -> str:
    return (
        name.lower().replace(" ", "-").replace("_", "-")
        .rstrip("-") or "asset"
    )


def load_manifest() -> dict:
    if MANIFEST_FILE.exists():
        try:
            return json.loads(MANIFEST_FILE.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            pass
    return {"schema_version": SCHEMA_VERSION, "generated_at": "", "assets": []}


def main() -> int:
    ap = argparse.ArgumentParser(description="Ref 资产库结构化迁移（dry-run 默认）")
    ap.add_argument("--apply", action="store_true", help="执行迁移（默认只打印计划）")
    ap.add_argument("--kind", choices=KINDS, default="characters",
                    help="顶层散图归类（默认 characters：本仓 Ref 均为人物参考）")
    args = ap.parse_args()
    apply = args.apply

    if not REF_DIR.exists():
        print(f"❌ 目录不存在：{REF_DIR}")
        return 2

    # 1) 收集顶层散图
    loose = sorted(
        p for p in REF_DIR.iterdir()
        if p.is_file() and p.suffix.lower() in IMG_EXT
    )
    # 2) 收集三类子目录既有文件（并入清单，缺条目补建）
    existing: dict[str, list[Path]] = {k: [] for k in KINDS}
    for k in KINDS:
        d = REF_DIR / k
        if d.is_dir():
            existing[k] = sorted(
                p for p in d.iterdir()
                if p.is_file() and p.suffix.lower() in IMG_EXT
            )

    actions: list[str] = []
    manifest = load_manifest()
    known_files = {f for a in manifest.get("assets", []) for f in a.get("files", [])}

    # 3) 计划：散图迁移
    for p in loose:
        dst = REF_DIR / args.kind / p.name
        actions.append(f"move  {p.name} -> {args.kind}/{p.name}")
    # 4) 计划：三类目录中未被清单收录的文件补建条目
    new_items = []
    for k, files in existing.items():
        for p in files:
            rel = f"{k}/{p.name}"
            if rel not in known_files:
                new_items.append((k, p))
                actions.append(f"index {rel}（补建清单条目）")
    for p in loose:  # 迁移后的新位置同样入清单
        rel = f"{args.kind}/{p.name}"
        if rel not in known_files:
            new_items.append((args.kind, p))

    now = datetime.now().astimezone().isoformat(timespec="seconds")
    if apply:
        for k in KINDS:
            (REF_DIR / k).mkdir(parents=True, exist_ok=True)
        for p in loose:
            shutil.move(str(p), str(REF_DIR / args.kind / p.name))
        for k, p in new_items:
            manifest["assets"].append({
                "id": slugify(p.stem),
                "kind": k,
                "name": p.stem,
                "files": [f"{k}/{p.name}"],
                "tags": [],
                "created_at": now,
                "updated_at": now,
            })
        manifest["schema_version"] = SCHEMA_VERSION
        manifest["generated_at"] = now
        manifest["assets"].sort(key=lambda a: (a["kind"], a["id"]))
        MANIFEST_FILE.write_text(
            json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
        )
        print(f"✅ 已执行：迁移 {len(loose)} 图 + 清单 {len(manifest['assets'])} 条目 → {MANIFEST_FILE.relative_to(REPO)}")
    else:
        print(f"[dry-run] 计划迁移 {len(loose)} 张散图（→ {args.kind}/），补建 {len(new_items)} 条清单条目：")
        for a in actions:
            print(f"  - {a}")
        print("（加 --apply 执行）")

    # 5) 结构自检（与 assets.ts 契约关键字段对齐）
    if apply:
        m = json.loads(MANIFEST_FILE.read_text(encoding="utf-8"))
        assert m["schema_version"] == 1 and isinstance(m["assets"], list)
        for a in m["assets"]:
            assert a["kind"] in KINDS and a["files"], a
            for f in a["files"]:
                assert (REF_DIR / f).is_file(), f"清单指向不存在文件：{f}"
        print(f"✅ 清单结构自检通过（{len(m['assets'])} 条目全部文件在位）")
    return 0


if __name__ == "__main__":
    sys.exit(main())
