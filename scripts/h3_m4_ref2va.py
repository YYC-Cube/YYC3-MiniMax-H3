# -*- coding: utf-8 -*-
"""
@file h3_m4_ref2va.py
@author YanYuCloudCube Team <admin@0379.email>
@version v1.1.0
@created 2026-09-02
@updated 2026-09-03
@status stable
@copyright Copyright (c) 2025-2026 YYC3 Team
@license MIT


M4 Max 128GB 优化版 Ref2VA 推理脚本（图/视频/音频参考模式：数字人口型、素材编辑）
来源：Mac-M4-Max-128GB-MiniMax-H3-NF4完整部署脚本.md
说明：参考图+提示词生成带口型说话视频
运行：python h3_m4_ref2va.py
注意：Ref2VA模式帧数必须满足 num_frames % 17 == 5，推荐124帧（官方默认）
"""
import torch
from PIL import Image
from diffsynth.pipelines.minimax_h3_audio_video import MiniMaxH3Pipeline, ModelConfig
from diffsynth.utils.data.audio_video import write_video_audio
from modelscope import dataset_snapshot_download


def align_frame_count(frame_count):
    current = max(int(frame_count), 1)
    while current % 17 != 5:
        current += 1
    return current


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

pipe = MiniMaxH3Pipeline.from_pretrained(
    torch_dtype=torch.bfloat16,
    device="mps",
    model_configs=[
        ModelConfig(model_id="DiffSynth-Studio/MiniMax-H3-NF4", origin_file_pattern="minimax-h3-ref2va-nf4.safetensors", **vram_config),
        ModelConfig(model_id="DiffSynth-Studio/MiniMax-H3-NF4", origin_file_pattern="minimax-h3-text-encoder-nf4.safetensors", **vram_config),
        ModelConfig(model_id="DiffSynth-Studio/MiniMax-H3-NF4", origin_file_pattern="video_vae_nf4.safetensors", **vram_config),
        ModelConfig(model_id="DiffSynth-Studio/MiniMax-H3-NF4", origin_file_pattern="audio_vae_nf4.safetensors", **vram_config),
    ],
    processor_config=ModelConfig(model_id="MiniMax/MiniMax-H3", origin_file_pattern="Ref2VA/processor/"),
    vram_limit=96,
)

# 下载示例参考素材
dataset_snapshot_download(dataset_id="DiffSynth-Studio/diffsynth_example_dataset", local_dir="data/diffsynth_example_dataset", allow_file_pattern="minimax_h3/MiniMax-H3-Ref2VA/*")
ref_image = Image.open("data/diffsynth_example_dataset/minimax_h3/MiniMax-H3-Ref2VA/0.png").convert("RGB")

prompt = "写实人像，年轻女性，自然口型同步说话，柔和自然光，稳定镜头"
video, audio = pipe(
    prompt=prompt,
    height=480, width=832, num_frames=124, num_inference_steps=50, seed=42,
    references=[{"type": "image", "image": ref_image}]
)
write_video_audio(
    video=video, audio=audio,
    output_path="ref2va_m4_output.mp4", fps=24, audio_sample_rate=32000,
)
print("✅ Ref2VA 视频生成完成 ref2va_m4_output.mp4")
