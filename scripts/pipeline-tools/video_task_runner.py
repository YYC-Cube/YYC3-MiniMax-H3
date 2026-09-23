# -*- coding: utf-8 -*-
"""
@file video_task_runner.py
@author YanYuCloudCube Team <admin@0379.email>
@version: v1.1.0
@created: 2026-09-24
@status: active
@copyright Copyright (c) 2025-2026 YYC3 Team
@license: MIT

video_task_runner.py — MiniMax-H3 第五能力 Mac runner（Phase 2.3）

网关任务队列（POST /v1/admin/video/tasks/claim）→ 夜间窗口生成 → 回报。
归档由网关侧完成（result 端点直写 NAS 卷），本 runner 不接触 NAS/ssh。

铁律（审核论证四修正）：
  ① Mac 生产任务限夜间窗口 22:00-08:00（白天仅 --dry-run / H3_FORCE=1 逃生阀）
  ② 与 nightly 批量互斥（pgrep batch_ref2va 检查，等空闲再领取）
  ③ 生成走 batch_ref2va_nf4.py --seeds 单 seed（任务式不跑双 seed）
  ④ 生成以 importlib 进程内加载批量脚本（sys.argv 注入 + cwd 隔离）——
     任务数据不进入任何子进程命令；任务 id 白名单 ^[0-9a-f]{6,16}$（防队列投毒）

用法：
  # 夜间 cron（22:05 起等空闲领取，最多跑到 07:30）：
  H3_VIDEO_RUNNER_KEY=<admin-key> python video_task_runner.py --loop
  # 单次领取（白天调试需 --dry-run）：
  H3_VIDEO_RUNNER_KEY=<admin-key> python video_task_runner.py --once
  # 干跑（跳过窗口/互斥/生成，用样片走全生命周期——e2e 测试用）：
  H3_VIDEO_RUNNER_KEY=<admin-key> python video_task_runner.py --once --dry-run
"""
import argparse
import base64
import os
import re
import shutil
import subprocess
import sys
import threading
import time
from pathlib import Path
from urllib.parse import urlparse

import requests

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
DEFAULT_REF = REPO_ROOT / "ref_images" / "person_a.png"
SAMPLE_MP4 = REPO_ROOT / "output_batch91" / "person_a" / "h3_seed_42.mp4"  # dry-run 样片
WORKROOT = Path.home() / "yyc3-video-tasks"

HEARTBEAT_SEC = 480  # 心跳间隔（租约 1/2 以内）

# 任务 id 白名单：网关生成的 uuid hex[:12]（防队列投毒）
_TID_RE = re.compile(r"^[0-9a-f]{6,16}$")


def _valid_tid(tid) -> bool:
    return bool(_TID_RE.match(tid or ""))


def _valid_gateway(url: str) -> bool:
    try:
        u = urlparse(url)
        return u.scheme in ("http", "https") and bool(u.netloc)
    except Exception:
        return False


def log(msg: str):
    print(f"[{time.strftime('%F %T')}] [runner] {msg}", flush=True)


def in_night_window() -> bool:
    if os.environ.get("H3_FORCE") == "1":
        return True
    h = time.localtime().tm_hour
    return h >= 22 or h < 8


def batch_busy() -> bool:
    r = subprocess.run(
        ["pgrep", "-f", "batch_ref2va_nf4.py"], capture_output=True, text=True
    )
    return r.returncode == 0


class Heartbeat:
    def __init__(self, gateway, key, task_id, runner):
        self.gateway, self.key, self.task_id, self.runner = gateway, key, task_id, runner
        self.stop = threading.Event()
        self.thread = threading.Thread(target=self._loop, daemon=True)

    def _loop(self):
        while not self.stop.wait(HEARTBEAT_SEC):
            try:
                requests.post(
                    f"{self.gateway}/v1/admin/video/tasks/{self.task_id}/heartbeat",
                    headers={"X-API-Key": self.key},
                    json={"runner": self.runner, "lease_minutes": 30},
                    timeout=15,
                )
                log(f"心跳 {self.task_id}")
            except Exception as e:  # 心跳失败不致命（租约有余量）
                log(f"心跳失败（非致命）: {e}")


def claim(gateway: str, key: str, runner: str):
    r = requests.post(
        f"{gateway}/v1/admin/video/tasks/claim",
        headers={"X-API-Key": key},
        json={"runner": runner, "lease_minutes": 180},
        timeout=20,
    )
    r.raise_for_status()
    task = (r.json() or {}).get("claimed")
    if task and not _valid_tid(task.get("id")):
        log(f"⚠️ 队列返回非法任务 id，拒绝处理：{task.get('id')!r}")
        return None
    return task


def report_failure(gateway: str, key: str, task_id: str, error: str):
    try:
        requests.post(
            f"{gateway}/v1/admin/video/tasks/{task_id}/failure",
            headers={"X-API-Key": key},
            json={"error": error[:1900]},
            timeout=20,
        )
    except Exception:
        pass


def run_generation(task: dict, workdir: Path) -> Path:
    """在独立工作目录跑单 seed 生成，返回 mp4 路径。

    安全实现：批量脚本以 importlib 进程内加载（sys.argv 注入 + cwd 切换隔离），
    全程无子进程命令拼接——任务数据（id/seed/prompt）不进入任何 exec 参数。
    批量脚本的 ref_images/output 均为相对路径，随 cwd 落在工作目录内。"""
    import importlib.util

    tid = task["id"]
    batch_id = f"vt{tid}"
    refdir = workdir / "ref_images"
    refdir.mkdir(parents=True, exist_ok=True)
    if task.get("ref_image_b64"):
        ref_name = task.get("ref_image_name") or "ref.png"
        if not re.match(r"^[\w.\-]{1,64}$", ref_name):  # 文件名白名单（防路径穿越）
            ref_name = "ref.png"
        (refdir / ref_name).write_bytes(base64.b64decode(task["ref_image_b64"]))
    else:
        shutil.copy(DEFAULT_REF, refdir / "person_a.png")

    seed = task.get("seed")
    seed = int(seed) if isinstance(seed, int) and 0 <= seed < 2**31 else 42

    argv = [
        "batch_ref2va_nf4.py",
        "--batch", batch_id,
        "--seeds", str(seed),
        "--variant", "pruned",
    ]
    if task.get("quality") == "preview":
        argv.append("--preview")
    if task.get("prompt"):
        pf = workdir / "prompt.txt"
        pf.write_text(str(task["prompt"])[:4000], encoding="utf-8")
        argv += ["--prompt-file", str(pf)]

    log(f"生成启动：batch={batch_id} quality={task.get('quality')} seed={seed}")
    t0 = time.time()

    prev_cwd, prev_argv = os.getcwd(), sys.argv
    try:
        os.chdir(workdir)
        sys.argv = argv
        spec = importlib.util.spec_from_file_location(
            f"h3gen_{tid}", str(REPO_ROOT / "scripts" / "batch_ref2va_nf4.py")
        )
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        mod.main()
    finally:
        os.chdir(prev_cwd)
        sys.argv = prev_argv

    videos = sorted((workdir / f"output_batch{batch_id}").rglob("h3_seed_*.mp4"))
    if not videos:
        raise RuntimeError("生成完成但未找到 mp4 产物")
    log(f"生成完成 {videos[0].name} 耗时 {time.time()-t0:.0f}s")
    return videos[0]


def process_task(gateway: str, key: str, task: dict, runner: str, dry_run: bool) -> bool:
    tid = task["id"]
    if not _valid_tid(tid):
        log(f"❌ 非法任务 id，丢弃：{tid!r}")
        return False
    log(f"领取任务 {tid} quality={task.get('quality')} seed={task.get('seed')}")
    hb = Heartbeat(gateway, key, tid, runner)
    hb.thread.start()
    t0 = time.time()
    try:
        if dry_run:
            log("DRY-RUN：跳过真实生成，使用 batch91 样片")
            if not SAMPLE_MP4.exists():
                raise RuntimeError(f"样片缺失 {SAMPLE_MP4}")
            mp4, duration = SAMPLE_MP4, 3.0
            time.sleep(2)
        else:
            workdir = WORKROOT / tid
            workdir.mkdir(parents=True, exist_ok=True)
            mp4 = run_generation(task, workdir)
            duration = time.time() - t0

        with open(mp4, "rb") as f:
            r = requests.post(
                f"{gateway}/v1/admin/video/tasks/{tid}/result",
                headers={"X-API-Key": key},
                files={"file": (f"{tid}.mp4", f, "video/mp4")},
                data={"duration_seconds": f"{duration:.1f}"},
                timeout=120,
            )
        r.raise_for_status()
        log(f"✅ 任务 {tid} 回报成功（归档由网关落盘）")
        if not dry_run:
            shutil.rmtree(WORKROOT / tid, ignore_errors=True)
        return True
    except Exception as e:
        log(f"❌ 任务 {tid} 失败: {e}")
        report_failure(gateway, key, tid, str(e))
        return False
    finally:
        hb.stop.set()


def main():
    ap = argparse.ArgumentParser(description="MiniMax-H3 视频任务 runner（第五能力 Phase 2.3）")
    ap.add_argument("--gateway", default=os.environ.get("H3_VIDEO_GATEWAY", "https://api.0379.world"),
                    help="公共网关（预留：状态查询等只读操作）")
    ap.add_argument("--admin-gateway",
                    default=os.environ.get("H3_VIDEO_ADMIN_GATEWAY", "http://192.168.3.45:8000"),
                    help="管理面直连地址（claim/heartbeat/result 走 LAN，绕开公网链大上传瓶颈；"
                         "09-24 e2e 实证 2.4MB multipart 经 ECS Traefik→Tailscale 90s 超时 499）")
    ap.add_argument("--runner-name", default=os.uname().nodename)
    ap.add_argument("--once", action="store_true", help="领取一个任务后退出（无任务也退出）")
    ap.add_argument("--loop", action="store_true", help="循环模式（夜间窗口内等空闲领取，至 07:30 截止）")
    ap.add_argument("--dry-run", action="store_true", help="干跑：样片走全生命周期（e2e 测试）")
    args = ap.parse_args()

    key = os.environ.get("H3_VIDEO_RUNNER_KEY", "")
    if not key:
        print("❌ 缺少 H3_VIDEO_RUNNER_KEY（网关 ADMIN_API_KEYS 中的 runner 密钥）", file=sys.stderr)
        sys.exit(2)
    if not (_valid_gateway(args.gateway) and _valid_gateway(args.admin_gateway)):
        print(f"❌ 网关 URL 非法（仅 http/https）：{args.gateway} / {args.admin_gateway}", file=sys.stderr)
        sys.exit(2)

    deadline = None
    if args.loop:
        now = time.localtime()
        if now.tm_hour >= 22 or now.tm_hour < 8:
            deadline = time.mktime(
                (now.tm_year, now.tm_mon, now.tm_mday + (1 if now.tm_hour >= 22 else 0),
                 7, 30, 0, 0, 0, -1)
            )

    while True:
        if args.dry_run:
            pass  # 干跑跳过窗口与互斥
        else:
            if not in_night_window():
                log("非夜间窗口（22:00-08:00），退出（铁律①；调试用 --dry-run 或 H3_FORCE=1）")
                sys.exit(0)
            if batch_busy():
                log("夜间批量占用中（铁律②），等待空闲…")
                time.sleep(300)
                continue
            if deadline and time.time() > deadline:
                log("已到 07:30 截止线，退出")
                sys.exit(0)

        try:
            task = claim(args.admin_gateway, key, args.runner_name)
        except Exception as e:
            log(f"领取失败：{e}")
            task = None
        if not task:
            if args.once or args.dry_run:
                log("队列无任务，退出")
                sys.exit(0)
            time.sleep(300)
            continue

        process_task(args.admin_gateway, key, task, args.runner_name, args.dry_run)
        if args.once or args.dry_run:
            sys.exit(0)


if __name__ == "__main__":
    main()
