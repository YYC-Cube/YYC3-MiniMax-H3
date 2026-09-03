# -*- coding: utf-8 -*-
"""
@file h3_pruned_ref2va_multi.py
@author YanYuCloudCube Team <admin@0379.email>
@version v1.1.0
@created 2026-09-02
@updated 2026-09-03
@status stable
@copyright Copyright (c) 2025-2026 YYC3 Team
@license MIT


Pruned Ref2VA｜批量多张参考图循环脚本（M4 Max）
来源：MiniMax-H3-DiffSynth本地版-提示词模板.md
功能：遍历多张参考图，每张图独立跑一组seed，按图片子目录归档（Pruned剪枝权重）
运行：python h3_pruned_ref2va_multi.py
"""
import torch
import os
from datetime import datetime
from PIL import Image
from diffsynth.pipelines.minimax_h3_audio_video import MiniMaxH3Pipeline, ModelConfig
from diffsynth.utils.data.audio_video import write_video_audio

# ========= M4 Max Pruned Ref2VA 配置 =========
vram_config = {
    "offload_dtype": "cpu",
    "offload_device": "cpu",
    "onload_dtype": torch.bfloat16,
    "onload_device": "mps",
    "preparing_dtype": torch.bfloat16,
    "preparing_device": "mps",
    "computation_dtype": torch.bfloat16,
    "computation_device": "mps",
}

# --------------------------
# 【配置区】
# --------------------------
ref_images_dir = "./ref_images"
supported_exts = [".jpg", ".jpeg", ".png", ".webp"]
output_root_dir = "./batch_output_ref2va_pruned"
seed_list = [42, 10, 24, 66, 88, 123]

prompt = """
主体定义：<Subject1>是参考图中的人物，面部五官、发型、服装全程保持不变，脸型稳定，不会变脸。
视频概要：固定机位半身人像，自然眨眼，嘴唇和对白精准同步，微小自然头部微动，不剧烈转头。
保留分析：锁定参考图人物五官、肤色、发型、服装，场景和光照全程保持不变。
详细画面描述：柔和自然光，浅景深，写实人像，高清皮肤质感，稳定构图，画面不抖动。
音频描述：<Subject1>清晰自然人声，语气平稳，台词："本地部署MiniMax H3，可以一次性生成同步语音与视频。"，安静环境，轻微底噪，无背景音乐。
禁止：五官崩坏、手部畸形、画面闪烁、人物身份漂移、镜头移动、剧烈转头
"""

height = 480
width = 832
num_frames = 124
num_inference_steps = 50

# --------------------------
# 加载 Pruned 模型：只加载一次
# --------------------------
pipe = MiniMaxH3Pipeline.from_pretrained(
    torch_dtype=torch.bfloat16,
    device="mps",
    model_configs=[
        ModelConfig(model_id="DiffSynth-Studio/MiniMax-H3-Pruned", origin_file_pattern="minimax-h3-ref2va-pruned.safetensors", **vram_config),
        ModelConfig(model_id="DiffSynth-Studio/MiniMax-H3-Pruned", origin_file_pattern="minimax-h3-text-encoder-pruned.safetensors", **vram_config),
        ModelConfig(model_id="DiffSynth-Studio/MiniMax-H3-Pruned", origin_file_pattern="video_vae-pruned.safetensors", **vram_config),
        ModelConfig(model_id="DiffSynth-Studio/MiniMax-H3-Pruned", origin_file_pattern="audio_vae-pruned.safetensors", **vram_config),
    ],
    processor_config=ModelConfig(model_id="MiniMax/MiniMax-H3", origin_file_pattern="Ref2VA/processor/"),
    vram_limit=96,
)

# --------------------------
# 遍历多张参考图
# --------------------------
if not os.path.exists(ref_images_dir):
    raise FileNotFoundError(f"参考图片目录不存在：{ref_images_dir}\n请先创建目录并放入人像图片。")

image_files = [
    f for f in os.listdir(ref_images_dir)
    if os.path.splitext(f)[1].lower() in supported_exts
]

if not image_files:
    raise FileNotFoundError(f"在目录 {ref_images_dir} 中未找到支持的图片文件。支持格式：{', '.join(supported_exts)}")

os.makedirs(output_root_dir, exist_ok=True)
log_path = os.path.join(output_root_dir, "batch_log.txt")

with open(log_path, "a", encoding="utf-8") as f:
    f.write("=" * 70 + "\n")
    f.write(f"【Pruned Ref2VA】批量多图任务启动时间：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
    f.write(f"参考图片目录：{ref_images_dir}\n")
    f.write(f"输出根目录：{output_root_dir}\n")
    f.write(f"分辨率：{width}x{height} | 帧数：{num_frames} | 推理步数：{num_inference_steps}\n")
    f.write(f"Seed列表：{', '.join(map(str, seed_list))}\n")
    f.write(f"Prompt:\n{prompt}\n")
    f.write("=" * 70 + "\n")

for img_file in image_files:
    img_stem = os.path.splitext(img_file)[0]
    img_path = os.path.join(ref_images_dir, img_file)
    output_dir = os.path.join(output_root_dir, img_stem)
    os.makedirs(output_dir, exist_ok=True)

    print(f"\n==========================")
    print(f"处理参考图：{img_file}")
    print(f"输出目录：{output_dir}")
    print(f"==========================")

    with open(log_path, "a", encoding="utf-8") as f:
        f.write(f"\n[{datetime.now()}] 开始处理图片：{img_file}\n")
        f.write(f"图片路径：{img_path}\n")
        f.write(f"输出目录：{output_dir}\n")

    try:
        ref_image = Image.open(img_path).convert("RGB")
    except Exception as e:
        print(f"❌ 无法打开图片：{img_file}，错误：{str(e)}")
        with open(log_path, "a", encoding="utf-8") as f:
            f.write(f"[{datetime.now()}] 图片读取失败：{img_file} | {str(e)}\n")
        continue

    for seed in seed_list:
        output_file = os.path.join(output_dir, f"h3_pruned_seed_{seed}.mp4")

        if os.path.exists(output_file):
            info = f"⏭️ {img_file} | Seed {seed} 已存在，跳过"
            print(info)
            with open(log_path, "a", encoding="utf-8") as f:
                f.write(f"[{datetime.now()}] {img_file} | Seed {seed} | SKIPPED | 文件已存在\n")
            continue

        print(f"---------- 当前 Seed: {seed} ----------")
        try:
            video, audio = pipe(
                prompt=prompt,
                height=height,
                width=width,
                num_frames=num_frames,
                num_inference_steps=num_inference_steps,
                seed=seed,
                references=[{"type": "image", "image": ref_image}]
            )
            write_video_audio(
                video=video,
                audio=audio,
                output_path=output_file,
                fps=24,
                audio_sample_rate=32000,
            )
            info = f"✅ {img_file} | Seed {seed} 完成 -> {output_file}"
            print(info)
            with open(log_path, "a", encoding="utf-8") as f:
                f.write(f"[{datetime.now()}] {img_file} | Seed {seed} | SUCCESS | {output_file}\n")
        except Exception as e:
            err_msg = f"❌ {img_file} | Seed {seed} 失败：{str(e)}"
            print(err_msg)
            with open(log_path, "a", encoding="utf-8") as f:
                f.write(f"[{datetime.now()}] {img_file} | Seed {seed} | FAILED | {str(e)}\n")

print("\n🎉 Pruned 批量多图任务完成！")
print(f"📝 日志文件：{log_path}")
