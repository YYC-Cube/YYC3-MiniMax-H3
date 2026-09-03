# -*- coding: utf-8 -*-
"""
@file batch_ref2va_nf4.py
@author YanYuCloudCube Team <admin@0379.email>
@version v1.1.0
@created 2026-09-02
@updated 2026-09-03
@status stable
@copyright Copyright (c) 2025-2026 YYC3 Team
@license MIT


batch_ref2va_nf4.py — Ref2VA 批量主生成脚本（manifest化版 · Phase 1 T1.1）
来源任务：docs/04-演进规划与闭环优化机制.md

相对旧版变化：
1. 每批次生成 manifest.json（单一事实源：参数/seed/状态/耗时/内存峰值全记录）
2. 性能采集：每个 seed 记录 gen_seconds / peak_rss_gb / mps_alloc_gb（T3.1 基线）
3. 接入共享库 scripts/lib/h3_common.py（模型加载/vram_config 收敛）
4. report_batchXX.md 增加「口型分」列（由 score_lipsync.py 生成后同步刷新）
5. 断点续跑逻辑保留：manifest 中 SUCCESS 的 seed 自动跳过

⚠️ 流水线规则保留：seed_list 必须单行书写（update_seed_list.py 正则依赖）
用法：python batch_ref2va_nf4.py --batch 01
"""
import argparse
import os
import sys
from pathlib import Path

# 共享库导入
sys.path.insert(0, str(Path(__file__).parent / "lib"))
from h3_common import (Manifest, PerformanceTimer, init_report, load_pipeline,
                       now_iso, report_row)

# ============================================================
# 批量参数配置区【按需修改】
# ============================================================
VARIANT = "nf4"          # nf4 | pruned
REF_IMAGES_DIR = Path("./ref_images")
SUPPORTED_EXTS = [".jpg", ".jpeg", ".png", ".webp"]

SEED_LIST = [42, 10]   # ⚠️ 保持单行，update_seed_list.py 依赖此格式；首次验证控制规模

PROMPT = """
主体定义：<Subject1>是参考图中的人物，面部五官、发型、服装全程保持不变，脸型稳定，不会变脸。
视频概要：固定机位半身人像，自然眨眼，嘴唇和对白精准同步，微小自然头部微动，不剧烈转头。
保留分析：锁定参考图人物五官、肤色、发型、服装，场景和光照全程保持不变。
详细画面描述：柔和自然光，浅景深，写实人像，高清皮肤质感，稳定构图，画面不抖动。
音频描述：<Subject1>清晰自然人声，语气平稳，台词："本地部署MiniMax H3，可以一次性生成同步语音与视频。"，安静环境，轻微底噪，无背景音乐。
禁止：五官崩坏、手部畸形、画面闪烁、人物身份漂移、镜头移动、剧烈转头
"""
HEIGHT = 480
WIDTH = 832
NUM_FRAMES = 124
NUM_INFERENCE_STEPS = 50
# ============================================================


def parse_args():
    ap = argparse.ArgumentParser(description="Ref2VA 批量生成（manifest化）")
    ap.add_argument("--batch", type=str, default="01", help="批次号，例如 01")
    return ap.parse_args()


def main():
    args = parse_args()
    batch = args.batch

    # ---------- 目录与文件规划（批次隔离） ----------
    output_root = Path(f"output_batch{batch}")
    output_root.mkdir(parents=True, exist_ok=True)
    report_md = Path(f"report_batch{batch}.md")
    manifest_path = output_root / "manifest.json"

    params = {
        "prompt": PROMPT.strip(),
        "height": HEIGHT, "width": WIDTH,
        "num_frames": NUM_FRAMES,
        "num_inference_steps": NUM_INFERENCE_STEPS,
        "seed_list": SEED_LIST,
        "ref_images_dir": str(REF_IMAGES_DIR),
        "fps": 24, "audio_sample_rate": 32000,
    }

    # ---------- manifest：断点续跑的关键 ----------
    if manifest_path.exists():
        manifest = Manifest.load(manifest_path)
        manifest.data["params"] = params  # 参数以最新一次运行为准
        print(f"📂 加载已有 manifest（{len(manifest.records)} 条记录），启用断点续跑")
    else:
        manifest = Manifest(manifest_path, batch=batch, variant=VARIANT, pipeline="ref2va", params=params)
    manifest.save()

    init_report(report_md, f"Ref2VA 批量生成结果报告（batch{batch}）",
                REF_IMAGES_DIR, SEED_LIST, output_root)

    # ---------- 扫描参考图 ----------
    if not REF_IMAGES_DIR.exists():
        raise FileNotFoundError(f"参考图片目录不存在：{REF_IMAGES_DIR}")
    image_files = [f for f in os.listdir(REF_IMAGES_DIR)
                   if Path(f).suffix.lower() in SUPPORTED_EXTS]
    if not image_files:
        raise FileNotFoundError(f"{REF_IMAGES_DIR} 中未找到图片，支持：{', '.join(SUPPORTED_EXTS)}")
    print(f"🖼️ 参考图 {len(image_files)} 张 × seed {len(SEED_LIST)} 个 = {len(image_files)*len(SEED_LIST)} 任务")

    # ---------- 模型：只加载一次 ----------
    print(f"⏳ 加载 {VARIANT} Ref2VA 模型（一次性）...")
    pipe = load_pipeline(variant=VARIANT, pipeline="ref2va")

    from diffsynth.utils.data.audio_video import write_video_audio
    from PIL import Image

    # ---------- 主循环 ----------
    for img_file in image_files:
        img_stem = Path(img_file).stem
        img_path = REF_IMAGES_DIR / img_file
        out_dir = output_root / img_stem
        out_dir.mkdir(parents=True, exist_ok=True)

        print(f"\n{'='*50}\n处理参考图：{img_file} → {out_dir}\n{'='*50}")
        try:
            ref_image = Image.open(img_path).convert("RGB")
        except Exception as e:
            print(f"❌ 图片读取失败：{img_file} | {e}")
            manifest.add_record(img_file, seed="-", status="READ_FAILED", video_path="-")
            manifest.save()
            continue

        for seed in SEED_LIST:
            video_path = out_dir / f"h3_seed_{seed}.mp4"
            rel_video = str(video_path)

            # 断点续跑：文件+manifest双确认
            existing = manifest.find(img_file, seed)
            if video_path.exists() and existing and existing["status"] == "SUCCESS":
                print(f"⏭️ {img_file} | Seed {seed} 已完成，跳过")
                continue

            print(f"---------- Seed {seed} ----------")
            try:
                with PerformanceTimer() as t:
                    video, audio = pipe(
                        prompt=PROMPT,
                        height=HEIGHT, width=WIDTH,
                        num_frames=NUM_FRAMES,
                        num_inference_steps=NUM_INFERENCE_STEPS,
                        seed=seed,
                        references=[{"type": "image", "image": ref_image}],
                    )
                    write_video_audio(video=video, audio=audio, output_path=str(video_path),
                                      fps=24, audio_sample_rate=32000)

                if existing:  # 重跑覆盖旧记录
                    existing.update(status="SUCCESS", video_path=rel_video,
                                    gen_seconds=t.seconds, peak_rss_gb=t.peak_rss_gb,
                                    mps_alloc_gb=t.mps_alloc_gb, time=__import__("h3_common", fromlist=["now_hms"]).now_hms())
                else:
                    manifest.add_record(img_file, seed, "SUCCESS", rel_video,
                                        gen_seconds=t.seconds, peak_rss_gb=t.peak_rss_gb,
                                        mps_alloc_gb=t.mps_alloc_gb)
                manifest.save()
                print(f"✅ 完成 -> {rel_video} | 耗时 {t.seconds}s | RSS峰值 {t.peak_rss_gb}GB")

                # report 行（口型分占位 '-'，score_lipsync.py 稍后回填刷新）
                if not existing:
                    with open(report_md, "a", encoding="utf-8") as f:
                        f.write(report_row(img_file, seed, "SUCCESS", rel_video))

            except Exception as e:
                print(f"❌ Seed {seed} 失败：{e}")
                if existing:
                    existing.update(status="FAILED", video_path=rel_video)
                else:
                    manifest.add_record(img_file, seed, "FAILED", rel_video)
                manifest.save()
                with open(report_md, "a", encoding="utf-8") as f:
                    f.write(report_row(img_file, seed, "FAILED", rel_video))

    manifest.finish()
    print(f"\n🎉 batch{batch} 生成完毕")
    print(f"📄 manifest：{manifest_path}")
    print(f"📋 report：{report_md}")
    print("→ 下一步：python score_lipsync.py --batch " + batch)


if __name__ == "__main__":
    main()
