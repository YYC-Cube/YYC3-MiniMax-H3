# -*- coding: utf-8 -*-
"""
@file h3_m4_fl2va_batch.py
@author YanYuCloudCube Team <admin@0379.email>
@version v1.1.0
@created 2026-09-02
@updated 2026-09-03
@status stable
@copyright Copyright (c) 2025-2026 YYC3 Team
@license MIT


批量Seed循环脚本 FL2VA版本（纯文生音视频批量脚本，适配M4 Max）
来源：MiniMax-H3-DiffSynth本地版-提示词模板.md
功能：循环多个seed批量生成，模型仅加载一次
运行：python h3_m4_fl2va_batch.py
"""
import torch
import os
from diffsynth.pipelines.minimax_h3_audio_video import MiniMaxH3Pipeline, ModelConfig
from diffsynth.utils.data.audio_video import write_video_audio
from PIL import Image

# ========= M4 Max 128GB 优化配置 =========
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

# 模型仅加载一次
pipe = MiniMaxH3Pipeline.from_pretrained(
    torch_dtype=torch.bfloat16,
    device="mps",
    model_configs=[
        ModelConfig(model_id="DiffSynth-Studio/MiniMax-H3-NF4", origin_file_pattern="minimax-h3-fl2va-nf4.safetensors", **vram_config),
        ModelConfig(model_id="DiffSynth-Studio/MiniMax-H3-NF4", origin_file_pattern="minimax-h3-text-encoder-nf4.safetensors", **vram_config),
        ModelConfig(model_id="DiffSynth-Studio/MiniMax-H3-NF4", origin_file_pattern="video_vae_nf4.safetensors", **vram_config),
        ModelConfig(model_id="DiffSynth-Studio/MiniMax-H3-NF4", origin_file_pattern="audio_vae_nf4.safetensors", **vram_config),
    ],
    processor_config=ModelConfig(model_id="MiniMax/MiniMax-H3", origin_file_pattern="FL2VA/processor/"),
    vram_limit=96,
)

# 批量配置
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

output_dir = "batch_output_fl2va"
os.makedirs(output_dir, exist_ok=True)

# 循环推理
for seed in seed_list:
    print(f"\n========== 当前 Seed: {seed} ==========")
    video, audio = pipe(
        prompt=prompt,
        height=height, width=width, num_frames=num_frames, num_inference_steps=num_inference_steps, seed=seed,
    )
    output_file = os.path.join(output_dir, f"h3_fl2va_seed_{seed}.mp4")
    write_video_audio(
        video=video, audio=audio,
        output_path=output_file, fps=24, audio_sample_rate=32000,
    )
    print(f"✅ Seed {seed} 生成完成 -> {output_file}")

print("\n🎉 FL2VA批量任务全部完成！")
