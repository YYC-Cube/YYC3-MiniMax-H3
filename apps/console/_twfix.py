#!/usr/bin/env python3
"""临时工具：Tailwind v4 简写迁移（[var(--x)] → (--x)，h-[480px]→h-120），执行后删除"""
import re
from pathlib import Path

BASE = Path("/Users/yanyu/YYC-Cube/YYC3-MiniMax-H3/apps/console/src/app")
FILES = [BASE / "layout.tsx", BASE / "page.tsx", BASE / "pipeline" / "page.tsx"]

PAT = re.compile(r"\[var\(--([a-z-]+)\)\]")

for f in FILES:
    t = f.read_text(encoding="utf-8")
    n1 = len(PAT.findall(t))
    t = PAT.sub(r"(--\1)", t)
    n2 = t.count("h-[480px]")
    t = t.replace("h-[480px]", "h-120")
    f.write_text(t, encoding="utf-8")
    print(f"{f.name}: var-shorthand={n1}, h-fix={n2}")
