# -*- coding: utf-8 -*-
"""
@file h3_pruned_ref2va_custom_ref.py
@author YanYuCloudCube Team <admin@0379.email>
@version v1.1.0
@created 2026-09-02
@updated 2026-09-03
@status stable
@copyright Copyright (c) 2025-2026 YYC3 Team
@license MIT


Pruned Ref2VA 脚本【自定义本地参考图 + 断点续跑 + 日志】
来源：MiniMax-H3-DiffSynth本地版-提示词模板.md
改动点：
1. 移除自动下载示例数据集，改为手动填写本地图片路径
2. 增加图片存在性校验，图片不存在直接抛出提示终止脚本
3. 保留原有全部能力：模型只加载一次、断点续跑、日志、异常捕获
运行：python h3_pruned_ref2va_custom_ref.py
"""
import torch
import os
from datetime import datetime
from PIL import Image
from diffsynth.pipelines.minimax_h3_audio_video import MiniMaxH3Pipeline, ModelConfig
from diffsynth.utils.data.audio_video import write_video_audio

# ========= M4 Max Pruned Ref2VA 显存配置 =========
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
# 【配置区：自定义本地参考图片路径，在这里修改】
# --------------------------
ref_img_path = "./ref_face.jpg"   # <- 修改这里！支持jpg/png
# 校验参考图是否存在
if not os.path.exists(ref_img_path):
    raise FileNotFoundError(f"参考图片不存在！路径：{ref_img_path}\n请检查文件路径是否正确")
ref_image = Image.open(ref_img_path).convert("RGB")

# --------------------------
# 加载 Pruned Ref2VA 模型（只加载一次）
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
# 【批量参数配置区｜直接在这里修改】
# --------------------------
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

output_dir = "batch_output_ref2va_pruned"
os.makedirs(output_dir, exist_ok=True)
log_path = os.path.join(output_dir, "batch_log.txt")

# 写入任务头部日志（追加模式，不覆盖旧日志）
with open(log_path, "a", encoding="utf-8") as f:
    f.write("="*60 + "\n")
    f.write(f"【Pruned Ref2VA】任务启动时间：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
    f.write(f"参考图片路径：{ref_img_path}\n")
    f.write(f"分辨率：{width}x{height} | 帧数：{num_frames} | 推理步数：{num_inference_steps}\n")
    f.write(f"Prompt:\n{prompt}\n")
    f.write("="*60 + "\n")

# --------------------------
# Seed循环｜断点续跑 + 异常捕获
# --------------------------
for seed in seed_list:
    output_file = os.path.join(output_dir, f"h3_pruned_seed_{seed}.mp4")
    # 断点续跑：文件存在直接跳过
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
            height=height,
            width=width,
            num_frames=num_frames,
            num_inference_steps=num_inference_steps,
            seed=seed,
            references=[{"type": "image", "image": ref_image}]
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

print("\n🎉 Pruned Ref2VA批量任务全部完成！")
print(f"📝 日志路径：{log_path}")
