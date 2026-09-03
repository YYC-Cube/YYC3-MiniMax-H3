# -*- coding: utf-8 -*-
"""
@file h3_m4_ref2va_batch.py
@author YanYuCloudCube Team <admin@0379.email>
@version v1.1.0
@created 2026-09-02
@updated 2026-09-03
@status stable
@copyright Copyright (c) 2025-2026 YYC3 Team
@license MIT


批量Seed循环脚本 Ref2VA版本（适配M4 Max）
来源：MiniMax-H3-DiffSynth本地版-提示词模板.md
功能：循环多个seed，自动生成不同版本视频，输出到独立文件夹，每个视频文件名带seed
核心：模型只加载一次（在循环外），避免重复加载巨大模型浪费内存/时间
运行：python h3_m4_ref2va_batch.py
"""
import torch
import os
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

# --------------------------
# 【只加载一次模型，在循环外！极大节省时间】
# --------------------------
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

# --------------------------
# 批量配置区，自行修改这里
# --------------------------
# 需要测试的seed列表，你可以自由增删
seed_list = [42, 10, 24, 66, 88, 123]
prompt = """
主体定义：<Subject1>是图中的年轻女生，面部五官、发型、服装全程保持不变，脸型稳定，不会变脸。
视频概要：固定机位半身人像，自然眨眼，嘴唇和对白精准同步，微小自然头部微动，不剧烈转头。
保留分析：锁定参考图人物五官、肤色、发型、衣服，场景和光照全程保持不变。
详细画面描述：柔和自然光，窗边环境，浅景深，写实人像，高清皮肤质感，稳定构图，画面不抖动。
音频描述：<Subject1>清晰英文人声，自然语气，台词："I enjoy working with DiffSynth-Studio, it's a perfect framework."，安静环境，轻微环境底噪，无配乐。
禁止：五官崩坏、手部畸形、画面闪烁、人物身份漂移、镜头移动
"""
height = 480
width = 832
num_frames = 124
num_inference_steps = 50

# 创建输出文件夹
output_dir = "batch_output_ref2va"
os.makedirs(output_dir, exist_ok=True)

# --------------------------
# 循环批量推理
# --------------------------
for seed in seed_list:
    print(f"\n========== 当前 Seed: {seed} ==========")
    video, audio = pipe(
        prompt=prompt,
        height=height,
        width=width,
        num_frames=num_frames,
        num_inference_steps=num_inference_steps,
        seed=seed,
        references=[{"type": "image", "image": ref_image}]
    )
    output_file = os.path.join(output_dir, f"h3_seed_{seed}.mp4")
    write_video_audio(
        video=video, audio=audio,
        output_path=output_file, fps=24, audio_sample_rate=32000,
    )
    print(f"✅ Seed {seed} 生成完成 -> {output_file}")

print("\n🎉 全部seed批量推理完成！视频保存在 batch_output_ref2va 文件夹")
