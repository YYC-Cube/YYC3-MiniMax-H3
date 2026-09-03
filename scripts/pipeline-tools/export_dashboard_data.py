#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
@file export_dashboard_data.py
@author YanYuCloudCube Team <admin@0379.email>
@version v1.0.0
@created 2026-09-03
@updated 2026-09-03
@status stable
@copyright Copyright (c) 2025-2026 YYC3 Team
@license MIT


export_dashboard_data.py — 可视化面板数据桥（方案A落地 · 见 docs/YYC3-MiniMax-H3-impl-expert-20260903/11-方案论证 §路线A）

职责：
  扫描 output_batch*/manifest.json → 聚合为 dashboard/data/batches.json
  面板 HTML fetch 该文件渲染真实数据；fetch 失败自动降级内置模拟数据（永不断流，对齐 score_lipsync 双后端策略）

评分刻度约定：
  - 口型分 score_norm ∈ (0,1) → 面板统一换算 10 分制：score_norm*10
  - 人工分 human.score 本身 1~10 → 直接使用
  - average 优先取人工分（缺失回退口型分），与 report「评分」列语义一致

用法：python export_dashboard_data.py   （或在项目根：python scripts/pipeline-tools/export_dashboard_data.py）
"""
import json
import sys
from datetime import datetime
from pathlib import Path

# ---- 路径解析：兼容「从任意 CWD 调用」，以脚本位置锚定仓库根 ----
TOOLS_DIR = Path(__file__).resolve().parent          # scripts/pipeline-tools/
REPO_ROOT = TOOLS_DIR.parent.parent                  # 仓库根
OUT_JSON = REPO_ROOT / "dashboard" / "data" / "batches.json"

DEFECT_TAG_FALLBACK = "未标注"


def load_manifests():
    """扫描全部 output_batch*/manifest.json，按批次号升序"""
    manifests = []
    for d in sorted(REPO_ROOT.glob("output_batch*")):
        mf = d / "manifest.json"
        if mf.exists():
            try:
                manifests.append(json.loads(mf.read_text(encoding="utf-8")))
            except (json.JSONDecodeError, OSError) as e:
                print(f"⚠️ 跳过损坏 manifest：{mf}（{e}）")
    return manifests


def display_score(rec: dict) -> tuple[float, str]:
    """返回 (0-10 展示分, 分数来源)"""
    human = rec.get("human") or {}
    if human.get("score") is not None:
        return float(human["score"]), "human"
    lip = rec.get("lipsync") or {}
    if lip.get("score_norm") is not None:
        return round(float(lip["score_norm"]) * 10, 1), "lipsync"
    return 0.0, "none"


def build_batch(m: dict) -> dict:
    """manifest → 面板 BATCHES 单元（字段与面板渲染函数一一对应）"""
    records = m.get("records", [])
    success = [r for r in records if r.get("status") == "SUCCESS"]
    failed = [r for r in records if r.get("status") not in ("SUCCESS", "SKIPPED")]
    skipped = [r for r in records if r.get("status") == "SKIPPED"]

    videos = []
    defect_counter: dict[str, int] = {}
    for r in success:
        score, source = display_score(r)
        tags = [t for t in (r.get("human") or {}).get("tags", "").replace("，", ",").split(",") if t.strip()]
        name = Path(r.get("video_path", "")).name
        videos.append({"name": name, "ref": r.get("ref_img", ""), "seed": r.get("seed"),
                       "score": score, "source": source, "tags": tags,
                       "video_path": r.get("video_path", ""),
                       "gen_seconds": r.get("gen_seconds"), "peak_rss_gb": r.get("peak_rss_gb"),
                       "av_offset": (r.get("lipsync") or {}).get("av_offset")})
        for t in tags:
            defect_counter[t] = defect_counter.get(t, 0) + 1

    scores = [v["score"] for v in videos if v["score"] > 0]
    avg = round(sum(scores) / len(scores), 2) if scores else 0.0
    mx = max(scores) if scores else 0.0

    started = m.get("started_at", "")
    ended = m.get("ended_at") or ""
    params = m.get("params", {})
    return {
        "id": f"batch{m.get('batch', '00')}",
        "time": (started.replace("T", " ")[:16]) if started else "",
        "ended": ended.replace("T", " ")[:16] or None,
        "model": (m.get("model", {}).get("variant") or "nf4").upper(),
        "pipeline": m.get("model", {}).get("pipeline", "ref2va"),
        "refImages": len({r.get("ref_img") for r in records if r.get("ref_img")}),
        "seeds": len({r.get("seed") for r in records}),
        "success": len(success), "failed": len(failed), "skipped": len(skipped),
        "avgScore": avg, "maxScore": mx,
        "status": "completed" if ended else "running",
        "videos": videos,
        "defects": dict(sorted(defect_counter.items(), key=lambda x: -x[1])),
        "params": {k: params.get(k) for k in
                   ("height", "width", "num_frames", "num_inference_steps", "fps") if k in params},
        "durationMin": _duration_min(started, ended),
    }


def _duration_min(started: str, ended: str) -> float | None:
    try:
        s = datetime.fromisoformat(started)
        e = datetime.fromisoformat(ended)
        return round((e - s).total_seconds() / 60, 1)
    except (ValueError, TypeError):
        return None


def build_top10(manifests: list[dict]) -> list[dict]:
    rows = []
    for m in manifests:
        for r in m.get("records", []):
            if r.get("status") != "SUCCESS":
                continue
            score, source = display_score(r)
            if score <= 0:
                continue
            rows.append({"batch": f"batch{m.get('batch','00')}", "img": r.get("ref_img", ""),
                         "seed": r.get("seed"), "score": score,
                         "tags": [t for t in (r.get("human") or {}).get("tags", "").split(",") if t.strip()]})
    rows.sort(key=lambda x: -x["score"])
    for i, r in enumerate(rows[:10], 1):
        r["rank"] = i
    return rows[:10]


def main():
    manifests = load_manifests()
    if not manifests:
        print("⚠️ 未找到任何 output_batch*/manifest.json（在仓库根 CWD 下运行），跳过导出")
        return 0  # 静默成功：面板将降级模拟数据

    batches = [build_batch(m) for m in manifests]
    payload = {
        "schema_version": 1,
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "score_scale": "0-10（lipsync score_norm×10 或 human 1~10）",
        "batches": batches,
        "top10": build_top10(manifests),
    }
    OUT_JSON.parent.mkdir(parents=True, exist_ok=True)
    OUT_JSON.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"✅ 面板数据已导出：{OUT_JSON.relative_to(REPO_ROOT)}（{len(batches)} 批次）")
    return 0


if __name__ == "__main__":
    sys.exit(main())
