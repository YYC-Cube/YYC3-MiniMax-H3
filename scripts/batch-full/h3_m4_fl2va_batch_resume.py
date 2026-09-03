# -*- coding: utf-8 -*-
"""
@file h3_m4_fl2va_batch_resume.py
@author YanYuCloudCube Team <admin@0379.email>
@version v1.1.0
@created 2026-09-02
@updated 2026-09-03
@status stable
@copyright Copyright (c) 2025-2026 YYC3 Team
@license MIT


FL2VA 完整版批量脚本【断点续跑 + seed日志】（M4 Max）
来源：MiniMax-H3-DiffSynth本地版-提示词模板.md
特性：
✅ 模型仅加载一次
✅ 断点续跑：文件已存在自动跳过
✅ 自动写入日志 batch_log.txt（追加模式，不覆盖旧日志）
✅ 输出目录：batch_output_fl2va
运行：python h3_m4_fl2va_batch_resume.py
"""
import torch
import os
from datetime import datetime
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
log_path = os.path.join(output_dir, "batch_log.txt")

# 写入任务头部信息
with open(log_path, "a", encoding="utf-8") as f:
    f.write("="*60 + "\n")
    f.write(f"任务启动时间：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
    f.write(f"分辨率：{width}x{height} | 帧数：{num_frames} | 推理步数：{num_inference_steps}\n")
    f.write(f"Prompt:\n{prompt}\n")
    f.write("="*60 + "\n")

# 循环推理 + 断点续跑 + 异常捕获
for seed in seed_list:
    output_file = os.path.join(output_dir, f"h3_fl2va_seed_{seed}.mp4")
    if os.path.exists(output_file):
        info = f"\n⏭️ Seed {seed} 文件已存在，跳过该任务: {output_file}"
        print(info)
        with open(log_path, "a", encoding="utf-8") as f:
            f.write(f"[{datetime.now()}] Seed {seed} | SKIPPED（文件已存在）\n")
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
        err_msg = f"❌ Seed {seed} 失败，错误信息：{str(e)}"
        print(err_msg)
        with open(log_path, "a", encoding="utf-8") as f:
            f.write(f"[{datetime.now()}] Seed {seed} | FAILED | {str(e)}\n")

print("\n🎉 FL2VA批量任务全部完成！")
print(f"📝 日志文件：{log_path}")
