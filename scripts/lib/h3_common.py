# -*- coding: utf-8 -*-
"""
@file h3_common.py
@author YanYuCloudCube Team <admin@0379.email>
@version v1.1.0
@created 2026-09-02
@updated 2026-09-03
@status stable
@copyright Copyright (c) 2025-2026 YYC3 Team
@license MIT


h3_common.py — MiniMax-H3 生产线共享库（Phase 1 · T1.1/T1.3）
来源任务：docs/04-演进规划与闭环优化机制.md

提供三大能力：
1. VramConfig / load_pipeline：M4 Max 统一模型加载入口（NF4/Pruned × FL2VA/Ref2VA）
2. Manifest：批次 manifest.json 单一事实源（schema_version=1）
3. PerformanceTimer：耗时 + 内存峰值采集（RSS / MPS 已分配显存）

manifest.json 结构：
{
  "schema_version": 1,
  "batch": "01",
  "model": {"variant": "nf4", "pipeline": "ref2va"},
  "params": {"height": 480, "width": 832, "num_frames": 124, "num_inference_steps": 50, "prompt": "..."},
  "started_at": "ISO8601",
  "ended_at": "ISO8601|null",
  "records": [
    {
      "ref_img": "person_a.jpg", "seed": 42, "status": "SUCCESS",
      "video_path": "output_batch01/person_a/h3_seed_42.mp4", "time": "14:30:21",
      "gen_seconds": 321.5, "peak_rss_gb": 41.2, "mps_alloc_gb": 12.3,
      "lipsync": {"backend": "syncnet", "confidence": 8.42, "av_offset": 3,
                  "score_norm": 0.63, "scored_at": "ISO8601"} | null,
      "human": {"score": null, "tags": ""}
    }
  ]
}
"""
import json
import os
import resource
import subprocess
import time
from datetime import datetime
from pathlib import Path
from typing import Optional

# ============================================================
# 模型加载（T1.3：收敛 19 个脚本的重复 vram_config/from_pretrained）
# ============================================================

MODEL_ID_NF4 = "DiffSynth-Studio/MiniMax-H3-NF4"
MODEL_ID_PRUNED = "DiffSynth-Studio/MiniMax-H3-Pruned"
PROCESSOR_ID = "MiniMax/MiniMax-H3"
# 本地权重根目录：存在 <root>/<model_id短名>/ 时直接用本地文件，避免重复下载
LOCAL_WEIGHTS_ROOT = os.environ.get("H3_WEIGHTS_DIR", "/Users/yanyu/models")


def m4_max_vram_config():
    """M4 Max 128GB 优化配置：CPU offload + MPS 计算（注意：device 必须是 torch.device 对象）"""
    import torch
    return {
        "offload_dtype": torch.float32,
        "offload_device": torch.device("cpu"),
        "onload_dtype": torch.bfloat16,
        "onload_device": torch.device("mps"),
        "preparing_dtype": torch.bfloat16,
        "preparing_device": torch.device("mps"),
        "computation_dtype": torch.bfloat16,
        "computation_device": torch.device("mps"),
    }


def weight_files(variant: str, pipeline: str):
    """按 variant(nf4|pruned) 和 pipeline(fl2va|ref2va) 返回权重清单"""
    sfx = "nf4" if variant == "nf4" else "pruned"
    dot = "-" if variant == "pruned" else "_"  # pruned文件名用连字符 video_vae-pruned
    return [
        f"minimax-h3-{pipeline}-{sfx}.safetensors",
        f"minimax-h3-text-encoder-{sfx}.safetensors",
        f"video_vae{dot}{sfx}.safetensors",
        f"audio_vae{dot}{sfx}.safetensors",
    ]


def _model_config(variant: str, files: list):
    """本地权重目录存在 → ModelConfig(path=具体文件)（跳过下载）；否则走 model_id 在线下载"""
    from diffsynth.pipelines.minimax_h3_audio_video import ModelConfig
    vc = m4_max_vram_config()
    model_id = MODEL_ID_NF4 if variant == "nf4" else MODEL_ID_PRUNED
    local_dir = Path(LOCAL_WEIGHTS_ROOT) / "MiniMax-H3-NF4"
    if (local_dir / files[0]).exists():
        return [ModelConfig(path=str(local_dir / f), **vc) for f in files]
    return [ModelConfig(model_id=model_id, origin_file_pattern=f, **vc) for f in files]


def load_pipeline(variant: str = "nf4", pipeline: str = "ref2va", vram_limit: int = 96):
    """统一模型加载入口。variant: nf4|pruned；pipeline: fl2va|ref2va"""
    import torch
    from diffsynth.pipelines.minimax_h3_audio_video import MiniMaxH3Pipeline, ModelConfig

    # processor：本地已下载则直接指向目录（避免在线下载），否则走 model_id
    local_proc = Path(LOCAL_WEIGHTS_ROOT) / "MiniMax-H3" / pipeline.upper() / "processor"
    proc_cfg = (ModelConfig(path=str(local_proc)) if (local_proc / "preprocessor_config.json").exists()
                else ModelConfig(model_id=PROCESSOR_ID, origin_file_pattern=f"{pipeline.upper()}/processor/"))
    return MiniMaxH3Pipeline.from_pretrained(
        torch_dtype=torch.bfloat16,
        device="mps",
        model_configs=_model_config(variant, weight_files(variant, pipeline)),
        processor_config=proc_cfg,
        vram_limit=vram_limit,
    )


# ============================================================
# 性能采集（T3.1 基线能力，随 T1.1 一并落地）
# ============================================================

class PerformanceTimer:
    """耗时 + 内存峰值。用法：with PerformanceTimer() as t: ..."""

    def __init__(self):
        self.start: float = 0.0
        self.seconds: float = 0.0
        self.peak_rss_gb: float = 0.0
        self.mps_alloc_gb: float | None = None

    def __enter__(self):
        self.start = time.perf_counter()
        return self

    def __exit__(self, *exc):
        self.seconds = round(time.perf_counter() - self.start, 3)
        # macOS ru_maxrss 单位为字节；保留3位小数避免小进程被舍入为0
        rss = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
        self.peak_rss_gb = round(rss / (1024 ** 3), 3)
        try:
            import torch
            if torch.backends.mps.is_available():
                self.mps_alloc_gb = round(float(torch.mps.current_allocated_memory()) / (1024 ** 3), 2)
        except Exception:
            pass
        return False


def now_iso() -> str:
    return datetime.now().isoformat(timespec="seconds")


def now_hms() -> str:
    return datetime.now().strftime("%H:%M:%S")


# ============================================================
# Manifest（T1.1：批次单一事实源）
# ============================================================

class Manifest:
    def __init__(self, path, batch="01", variant="nf4", pipeline="ref2va", params=None):
        self.path = Path(path)
        self.data = {
            "schema_version": 1,
            "batch": str(batch),
            "model": {"variant": variant, "pipeline": pipeline},
            "params": params or {},
            "started_at": now_iso(),
            "ended_at": None,
            "records": [],
        }

    # ---------- 基础IO ----------
    @classmethod
    def load(cls, path):
        m = cls.__new__(cls)
        m.path = Path(path)
        m.data = json.loads(m.path.read_text(encoding="utf-8"))
        return m

    def save(self):
        self.path.parent.mkdir(parents=True, exist_ok=True)
        tmp = self.path.with_suffix(".json.tmp")
        tmp.write_text(json.dumps(self.data, ensure_ascii=False, indent=2), encoding="utf-8")
        tmp.replace(self.path)  # 原子写，断电不损坏

    @property
    def records(self):
        return self.data["records"]

    # ---------- 记录操作 ----------
    def add_record(self, ref_img, seed, status, video_path, **perf):
        rec = {
            "ref_img": ref_img,
            "seed": seed,
            "status": status,  # SUCCESS | FAILED | SKIPPED | READ_FAILED
            "video_path": video_path,
            "time": now_hms(),
            "gen_seconds": perf.get("gen_seconds"),
            "peak_rss_gb": perf.get("peak_rss_gb"),
            "mps_alloc_gb": perf.get("mps_alloc_gb"),
            "lipsync": None,   # 由 score_lipsync.py 回填
            "human": {"score": None, "tags": ""},  # 人工打分回填
        }
        self.records.append(rec)
        return rec

    def find(self, ref_img, seed):
        for r in self.records:
            if r["ref_img"] == ref_img and str(r["seed"]) == str(seed):
                return r
        return None

    def set_lipsync(self, ref_img, seed, backend, confidence, av_offset, score_norm):
        rec = self.find(ref_img, seed)
        if rec:
            rec["lipsync"] = {
                "backend": backend,
                "confidence": confidence,
                "av_offset": av_offset,
                "score_norm": score_norm,
                "scored_at": now_iso(),
            }

    def set_human(self, ref_img, seed, score=None, tags=None):
        rec = self.find(ref_img, seed)
        if rec:
            if score is not None:
                rec["human"]["score"] = score
            if tags is not None:
                rec["human"]["tags"] = tags

    def finish(self):
        self.data["ended_at"] = now_iso()
        self.save()

    # ---------- 导出（兼容 analyze / 面板） ----------
    def flat_rows(self):
        """展平为行记录，lipsync/human 拆列，供 analyze 直接消费"""
        for r in self.records:
            lip = r.get("lipsync") or {}
            hu = r.get("human") or {}
            yield {
                "ref_img": r["ref_img"],
                "seed": r["seed"],
                "status": r["status"],
                "video_path": r["video_path"],
                "time": r["time"],
                "lipsync_score": lip.get("score_norm"),
                "lipsync_confidence": lip.get("confidence"),
                "lipsync_backend": lip.get("backend"),
                "gen_seconds": r.get("gen_seconds"),
                "score": hu.get("score"),
                "tags": hu.get("tags") or "",
            }


# ============================================================
# 报告表格（report_batchXX.md，新增「口型分」列，与 manifest 同步）
# ============================================================

REPORT_HEADER = "| 参考图 | Seed | 状态 | 视频相对路径 | 时间 | 口型分 | 评分(1~10) | 缺陷标签 |"
REPORT_SEP = "|--------|------|------|--------------|------|--------|------------|----------|"


def init_report(md_path: Path, title: str, ref_images_dir, seed_list, output_root_dir):
    if not md_path.exists():
        with open(md_path, "w", encoding="utf-8") as f:
            f.write(f"# {title}\n\n")
            f.write(f"任务启动：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write(f"参考图目录：`{ref_images_dir}`\n")
            f.write(f"视频输出目录：`{output_root_dir}`\n")
            f.write(f"Seed列表：{seed_list}\n\n")
            f.write(REPORT_HEADER + "\n")
            f.write(REPORT_SEP + "\n")


def report_row(ref_img, seed, status, video_path, lipsync="-"):
    """lipsync: score_norm(0~1) 或 '-'"""
    return f"| {ref_img} | {seed} | {status} | `{video_path}` | {now_hms()} | {lipsync} |  |  |\n"


# ============================================================
# 启发式音画同步代理分（score_lipsync 的降级后端）
# ============================================================

def extract_audio_wav(video_path: Path, wav_path: Path, sr: int = 16000) -> bool:
    """用 ffmpeg 提取单声道 wav。失败返回 False。"""
    try:
        subprocess.run(
            ["ffmpeg", "-y", "-loglevel", "error", "-i", str(video_path),
             "-ac", "1", "-ar", str(sr), "-vn", str(wav_path)],
            check=True, capture_output=True,
        )
        return wav_path.exists()
    except Exception:
        return False


def heuristic_sync_score(video_path: Path, work_dir: Path) -> dict:
    """
    无SyncNet权重时的降级方案：
    音频RMS能量包络 vs 视频口型区运动能量 的分段相关系数 → 归一化到 0~1。
    返回 {"backend": "heuristic", "confidence": corr, "av_offset": 0, "score_norm": x}
    """
    import cv2
    import numpy as np
    import wave

    video_path = Path(video_path)
    work_dir = Path(work_dir)
    work_dir.mkdir(parents=True, exist_ok=True)
    wav_path = work_dir / f"{video_path.stem}_audio.wav"

    if not extract_audio_wav(video_path, wav_path):
        return {"backend": "heuristic", "confidence": None, "av_offset": 0, "score_norm": None}

    # 1) 音频RMS包络
    with wave.open(str(wav_path), "rb") as w:
        sr = w.getframerate()
        n = w.getnframes()
        audio = np.frombuffer(w.readframes(n), dtype=np.int16).astype(np.float32) / 32768.0
    dur = n / max(sr, 1)
    if dur < 1.0:
        return {"backend": "heuristic", "confidence": None, "av_offset": 0, "score_norm": None}

    # 2) 口型区运动能量（画面中下部裁剪帧行人代表区域）
    cap = cv2.VideoCapture(str(video_path))
    frame_energies = []
    prev = None
    while True:
        ok, frame = cap.read()
        if not ok:
            break
        h, w_ = frame.shape[:2]
        mouth = frame[int(h * 0.55):int(h * 0.90), int(w_ * 0.25):int(w_ * 0.75)]
        gray = cv2.cvtColor(mouth, cv2.COLOR_BGR2GRAY).astype(np.float32)
        if prev is not None:
            frame_energies.append(float(np.mean(np.abs(gray - prev))))
        prev = gray
    cap.release()
    if len(frame_energies) < 10:
        return {"backend": "heuristic", "confidence": None, "av_offset": 0, "score_norm": None}

    # 3) 帧级对齐：两路信号都转成「活跃度」事件轨道，用事件级最近邻匹配评分。
    #    根因笔记：
    #    - Pearson相关在稀疏二值脉冲上即使完全重合也很低（大量双零帧压低协方差）；
    #    - AAC编码会让音轨时长轻微漂移（实测2s内容→2.05s），后段事件累计偏移1帧，
    #      固定滞后的全局Jaccard也无法吸收这种渐进漂移。
    #    解法：事件集合的最近邻匹配（事件|偏差|<=tol即算命中），对渐进漂移鲁棒。
    n_frames = len(frame_energies) + 1
    # 音频插值到帧级，取逐帧能量（差分）→ 活跃度（发声 onset/offset 事件）
    a_frame = np.interp(np.linspace(0, len(audio) - 1, n_frames), np.arange(len(audio)), audio)
    a_act_raw = np.abs(np.diff(a_frame))
    a_thr = max(0.3 * a_act_raw.std(), 1e-4)
    a_active = (a_act_raw > a_thr).astype(np.float32)

    # 视频能量 → 活跃度（口型运动事件）
    v_e = np.array(frame_energies, dtype=np.float32)
    v_thr = max(0.3 * v_e.std(), 1e-4)
    v_active = (v_e > v_thr).astype(np.float32)

    k = min(len(a_active), len(v_active))
    if k < 8 or a_active.std() < 1e-6 or v_active.std() < 1e-6:
        return {"backend": "heuristic", "confidence": None, "av_offset": 0, "score_norm": None}

    tol = 1  # 事件匹配容差（帧）
    a_events = [i for i in range(k) if a_active[i] > 0]
    v_events = [i for i in range(k) if v_active[i] > 0]
    if not a_events or not v_events:
        return {"backend": "heuristic", "confidence": None, "av_offset": 0, "score_norm": None}

    # 事件级最近邻匹配：任一方向被tol内最近邻命中即算匹配
    matched_a = sum(1 for i in a_events if any(abs(i - j) <= tol for j in v_events))
    matched_v = sum(1 for j in v_events if any(abs(j - i) <= tol for i in a_events))
    total_events = len(a_events) + len(v_events)
    corr = (matched_a + matched_v) / total_events if total_events else 0.0
    best_lag = 0

    return {
        "backend": "heuristic",
        "confidence": round(corr, 4),
        "av_offset": best_lag,
        "score_norm": round((corr + 1) / 2, 4),  # [-1,1] → [0,1]
    }


def syncnet_score(video_path: Path, work_dir: Path) -> Optional[dict]:
    """
    SyncNet 后端（优先）。依赖 pip install syncnet-python + 权重。
    score_norm = conf / (abs(conf) + 5)，conf≈10（官方demo量级）→ 0.67
    不可用时返回 None，由调用方降级。

    实现说明：不调用 pl.inference()（其内部 scene 分段 + 逐段 _track 在
    本项目视频上会 0 成轨，见 syncnet_score_impl 的根因笔记），
    而是用全局检测一次性喂 _track 后走 crop→evaluate。
    """
    return syncnet_score_impl(video_path, work_dir)


def syncnet_score_impl(video_path: Path, work_dir: Path) -> Optional[dict]:
    # syncnet 0.2.2 的 __init__ 在子模块导入失败时静默置 SyncNetPipeline=None，
    # 必须从子模块导入以暴露真实 ImportError（如 scenedetect>=0.7 移除了 video_manager）
    try:
        from syncnet_python.syncnet_pipeline import PipelineConfig, SyncNetPipeline
    except ImportError:
        return None
    try:
        import ffmpeg as ffmpeg_py

        device = "cpu"  # M4 Max 上 CPU 稳定；权重小，离线批量不阻塞生成
        # 权重路径：项目根 models/syncnet/（sfd_face.pth + syncnet_v2.model，
        # 来自 Oxford VGG lipsync 页面）；PipelineConfig 用相对路径，须显式指定
        weights_dir = Path(__file__).resolve().parents[2] / "models" / "syncnet"
        sfd = weights_dir / "sfd_face.pth"
        snw = weights_dir / "syncnet_v2.model"
        if not (sfd.exists() and snw.exists()):
            return None
        # 本项目480x832半身像实测脸宽仅~55px（默认100是LRS2大特写口径，会让track全灭），
        # 且AI视频口型开合引起 IoU<0.5 频繁断轨（实测单轨最长49帧），故：
        #   min_face_size 40（尺寸门槛）+ min_track 25（轨长门槛）+ num_failed_det 50（断轨容忍）
        cfg = PipelineConfig(s3fd_weights=str(sfd), syncnet_weights=str(snw),
                             min_face_size=40, min_track=25, num_failed_det=50)
        pl = SyncNetPipeline(cfg, device=device)

        work_dir.mkdir(parents=True, exist_ok=True)
        # ① 恒定25fps AVI（复刻 pipeline 预处理）
        avi = work_dir / "video.avi"
        ffmpeg_py.input(str(video_path)).output(
            str(avi), **{"q:v": 2}, r=cfg.frame_rate, **{"async": 1}
        ).overwrite_output().run(quiet=True)
        # ② 抽帧
        frames_dir = work_dir / "frames"
        frames_dir.mkdir(exist_ok=True)
        ffmpeg_py.input(str(avi)).output(
            str(frames_dir / "%06d.jpg"), **{"q:v": 2}, f="image2", threads=1
        ).overwrite_output().run(quiet=True)
        frames = sorted(frames_dir.glob("*.jpg"))
        if not frames:
            return None
        # ③ 音频 16k mono wav
        wav = work_dir / "speech.wav"
        ffmpeg_py.input(str(video_path)).output(
            str(wav), ac=1, ar=cfg.audio_sample_rate, format="wav"
        ).overwrite_output().run(quiet=True)
        # ④ 人脸检测（全局帧号）
        import cv2
        detections = []
        for i, fp in enumerate(frames):
            img = cv2.imread(str(fp))
            boxes = (pl.s3fd.detect_faces(
                cv2.cvtColor(img, cv2.COLOR_BGR2RGB),
                conf_th=0.9, scales=[cfg.facedet_scale]) if img is not None else [])
            detections.append([
                {"frame": i, "bbox": b[:-1].tolist(), "conf": float(b[-1])}
                for b in boxes
            ])
        if not any(detections):
            return None
        # ⑤ 关键差异：全局一次性 _track（绕过 scene 分段；分段会 0 成轨）
        #    根因笔记：scenedetect 把 124 帧口播视频切成多段，每段独立 _track 的
        #    种子链在 IoU<0.5 断点即弃轮，段内剩余脸帧数 < min_track → 全部丢弃；
        #    全局模式允许轨跨越场景边界，实测 seed42 能成 2 条轨（1-123 / 6-81）
        tracks = pl._track(detections)
        if not tracks:
            return None
        # ⑥ crop → evaluate
        confs, offsets = [], []
        for i, t in enumerate(tracks):
            cp = pl._crop(t, frames, str(wav), work_dir / "cropped" / f"{i:05d}")
            crop_dir = work_dir / "cropped" / f"crop_{i:05d}"
            crop_dir.mkdir(parents=True, exist_ok=True)
            ffmpeg_py.input(cp).output(str(crop_dir / "%06d.jpg"), f="image2", threads=1).overwrite_output().run(quiet=True)
            ffmpeg_py.input(cp).output(str(crop_dir / "audio.wav"), ac=1, vn=None,
                                       acodec="pcm_s16le", ar=16000,
                                       af="aresample=async=1").overwrite_output().run(quiet=True)
            class _Opt:
                tmp_dir = ""
                batch_size = 0
                vshift = 0
            opt = _Opt()
            opt.tmp_dir = str(crop_dir)
            opt.batch_size = cfg.batch_size
            opt.vshift = cfg.vshift
            off, conf, _dist = pl.syncnet.evaluate(opt=opt)
            confs.append(conf)
            offsets.append(off)
        if not confs:
            return None
        best_i = max(range(len(confs)), key=lambda k: confs[k])
        conf = float(confs[best_i])
        return {
            "backend": "syncnet",
            "confidence": round(conf, 4),
            "av_offset": int(offsets[best_i]),
            "score_norm": round(conf / (abs(conf) + 5.0), 4),
        }
    except Exception:
        return None
