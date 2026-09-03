# -*- coding: utf-8 -*-
"""
@file h3_pruned_fl2va_batch_resume.py
@author YanYuCloudCube Team <admin@0379.email>
@version v1.1.0
@created 2026-09-02
@updated 2026-09-03
@status stable
@copyright Copyright (c) 2025-2026 YYC3 Team
@license MIT


Pruned 精简版 FL2VA 批量脚本（断点续跑 + 日志）
来源：MiniMax-H3-DiffSynth本地版-提示词模板.md
说明：Pruned FL2VA：纯文本生成音视频，剪枝权重，内存占用更低
输出：batch_output_fl2va_pruned（与NF4版本视频隔离）
运行：python h3_pruned_fl2va_batch_resume.py
"""
import torch
import os
from datetime import datetime
from diffsynth.pipelines.minimax_h3_audio_video import MiniMaxH3Pipeline, ModelConfig
from diffsynth.utils.data.audio_video import write_video_audio
from PIL import Image

# ========= M4 Max Pruned FL2VA 显存配置 =========
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
# 加载 Pruned FL2VA 模型（仅加载一次）
# --------------------------
pipe = MiniMaxH3Pipeline.from_pretrained(
    torch_dtype=torch.bfloat16,
    device="mps",
    model_configs=[
        ModelConfig(model_id="DiffSynth-Studio/MiniMax-H3-Pruned", origin_file_pattern="minimax-h3-fl2va-pruned.safetensors", **vram_config),
        ModelConfig(model_id="DiffSynth-Studio/MiniMax-H3-Pruned", origin_file_pattern="minimax-h3-text-encoder-pruned.safetensors", **vram_config),
        ModelConfig(model_id="DiffSynth-Studio/MiniMax-H3-Pruned", origin_file_pattern="video_vae-pruned.safetensors", **vram_config),
        ModelConfig(model_id="DiffSynth-Studio/MiniMax-H3-Pruned", origin_file_pattern="audio_vae-pruned.safetensors", **vram_config),
    ],
    processor_config=ModelConfig(model_id="MiniMax/MiniMax-H3", origin_file_pattern="FL2VA/processor/"),
    vram_limit=96,
)

# --------------------------
# 批量参数配置区
# --------------------------
seed_list = [0, 1, 5, 16, 42, 99]
prompt = """
画面：固定机位半身年轻亚洲女性，柔和室内柔光，白色背景，写实摄影，皮肤质感真实，缓慢眨眼，嘴唇与台词同步，微小头部微动，构图稳定，画面无闪烁。
音频：清晰中文女声，语速适中，台词："本地部署MiniMax H3，可以一次性生成同步语音与视频。"，安静室内环境底噪，无背景音乐。
禁止：五官扭曲、手部畸形、换脸、镜头推拉、剧烈动作
"""
height = 480
width = 832
num_frames = 124
num_inference_steps = 50

output_dir = "batch_output_fl2va_pruned"
os.makedirs(output_dir, exist_ok=True)
log_path = os.path.join(output_dir, "batch_log.txt")

# 写入任务头部日志
with open(log_path, "a", encoding="utf-8") as f:
    f.write("="*60 + "\n")
    f.write(f"【Pruned FL2VA】任务启动时间：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
    f.write(f"分辨率：{width}x{height} | 帧数：{num_frames} | 推理步数：{num_inference_steps}\n")
    f.write(f"Prompt:\n{prompt}\n")
    f.write("="*60 + "\n")

# --------------------------
# Seed循环｜断点续跑 + 异常捕获
# --------------------------
for seed in seed_list:
    output_file = os.path.join(output_dir, f"h3_fl2va_pruned_seed_{seed}.mp4")
    if os.path.exists(output_file):
        info = f"\n⏭️ Seed {seed} 文件已存在，跳过任务: {output_file}"
        print(info)
        with open(log_path, "a", encoding="utf-8") as f:
            f.write(f"[{datetime.now()}] Seed {seed} | SKIPPED 文件已存在\n")
        continue

    print(f"\n========== 当前 Seed: {seed} ==========")
    try:
        video, audio = pipe(
            prompt=prompt,
            height=height, width=width, num_frames=num_frames, num_inference_steps=num_inference_steps, seed=seed,
        )
        write_video_audio(
            video=video, audio=audio,
            output_path=output_file, fps=24, audio_sample_rate=32000,
        )
        info = f"✅ Seed {seed} 生成完成 -> {output_file}"
        print(info)
        with open(log_path, "a", encoding="utf-8") as f:
            f.write(f"[{datetime.now()}] Seed {seed} | SUCCESS | {output_file}\n")
    except Exception as e:
        err_msg = f"❌ Seed {seed} 失败，错误：{str(e)}"
        print(err_msg)
        with open(log_path, "a", encoding="utf-8") as f:
            f.write(f"[{datetime.now()}] Seed {seed} | FAILED | {str(e)}\n")

print("\n🎉 Pruned FL2VA批量任务全部完成！")
print(f"📝 日志路径：{log_path}")
