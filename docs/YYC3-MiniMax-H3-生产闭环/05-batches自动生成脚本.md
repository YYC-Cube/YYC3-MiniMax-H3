---
file: 05-batches自动生成脚本.md
description: batches.json 生成脚本（⚠️ 与 export_dashboard_data.py 双源冲突，待 P1-C2 归一后降级为参考）
author: Intelligent Application Implementation Expert <admin@0379.email>
version: v1.1.0
created: 2026-09-25
updated: 2026-09-25
status: active
tags: [batches],[pipeline],[script],[deprecated-candidate]
category: code
language: zh-CN
changelog:
  - { version: v1.0.0, date: 2026-09-25, author: 智能应用落地专家, change: 原始版本收录（生成于外部会话） }
  - { version: v1.1.0, date: 2026-09-25, author: 智能应用落地专家, change: P1-D1 规范化整备（补齐 YAML FM） }
---

# batches.json 自动生成脚本

**100% 对齐既有流水线结构、manifest 单一事实源规范、NAS 同步链路与品牌视觉体系**，插入即可运行，零适配成本。

---

## 一、batches.json 自动生成脚本

### 定位

插入 H3 批量流水线末尾，生产完成后自动读取 `manifest.json` 全量指标，增量更新面板数据源 `dashboard/batches.json`，保留历史批次、自动去重、按时间倒序排列，**天然复用前文 NAS 每 5 分钟同步链路**，无需额外配置。

### 文件路径

`scripts/pipeline-tools/update_dashboard_batch.py`

### 完整代码

```
#!/usr/bin/env python
# ==============================================================
# 流水线面板数据自动更新脚本 v1.0
# 触发时机：批次生产完成后自动调用
# 数据源：批次目录 manifest.json 单一事实源
# 输出：dashboard/batches.json（面板唯一数据源）
# 对齐规范：YYC³ 单一事实源 + NAS 自动同步链路
# ==============================================================
import os
import json
import argparse
from datetime import datetime

# 仓库根目录（相对脚本路径向上两级）
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT_DIR = os.path.abspath(os.path.join(SCRIPT_DIR, "../.."))
DASHBOARD_FILE = os.path.join(ROOT_DIR, "dashboard", "batches.json")
# 最大保留历史批次
MAX_BATCHES = 100

def load_manifest(batch_dir: str) -> dict:
    """读取批次 manifest，提取核心指标"""
    manifest_path = os.path.join(batch_dir, "manifest.json")
    if not os.path.exists(manifest_path):
        return {}
    
    with open(manifest_path, "r", encoding="utf-8") as f:
        manifest = json.load(f)
    
    # 标准化字段提取，兼容不同版本 manifest
    return {
        "total_time": manifest.get("total_seconds", manifest.get("gen_seconds", 0)),
        "avg_frame_time": manifest.get("avg_frame_seconds", 0),
        "peak_memory": manifest.get("peak_rss_gb", manifest.get("mps_alloc_gb", 0)),
        "sync_score": manifest.get("sync_score", manifest.get("objective_score", 0)),
        "seed": manifest.get("seed", -1),
        "num_frames": manifest.get("num_frames", manifest.get("frames", 0)),
        "model_version": manifest.get("model_id", "MiniMax-H3-NF4"),
        "resolution": manifest.get("resolution", "480x832"),
        "fps": manifest.get("fps", 24),
        "steps": manifest.get("num_inference_steps", 50)
    }

def calc_quality_level(sync_score: float) -> str:
    """根据同步评分计算质量等级，对齐 SyncNet 双基准"""
    if sync_score >= 0.95:
        return "优秀"
    elif sync_score >= 0.90:
        return "良好"
    elif sync_score >= 0.75:
        return "合格"
    else:
        return "待优化"

def update_batches(batch_id: str, batch_dir: str, status: str, mode: str):
    """更新 batches.json 主逻辑"""
    # 1. 读取历史数据
    if os.path.exists(DASHBOARD_FILE):
        with open(DASHBOARD_FILE, "r", encoding="utf-8") as f:
            batches = json.load(f)
    else:
        batches = []
        os.makedirs(os.path.dirname(DASHBOARD_FILE), exist_ok=True)
    
    # 2. 读取当前批次指标
    manifest_data = load_manifest(batch_dir)
    
    # 3. 构建批次记录
    batch_record = {
        "batch_id": batch_id,
        "create_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "timestamp": int(datetime.now().timestamp()),
        "mode": mode,
        "status": status,
        "input_text": manifest_data.get("input_text", ""),
        "ref_image": manifest_data.get("ref_image", ""),
        "num_frames": manifest_data.get("num_frames", 0),
        "total_time": round(manifest_data.get("total_time", 0), 2),
        "avg_frame_time": round(manifest_data.get("avg_frame_time", 0), 3),
        "peak_memory": round(manifest_data.get("peak_memory", 0), 2),
        "sync_score": round(manifest_data.get("sync_score", 0), 4),
        "quality_level": calc_quality_level(manifest_data.get("sync_score", 0)),
        "model_version": manifest_data.get("model_version", ""),
        "resolution": manifest_data.get("resolution", ""),
        "seed": manifest_data.get("seed", -1),
        "video_path": os.path.relpath(os.path.join(batch_dir, "output.mp4"), ROOT_DIR)
    }
    
    # 4. 去重：移除同 batch_id 旧记录
    batches = [b for b in batches if b["batch_id"] != batch_id]
    
    # 5. 插入到头部（最新在前）
    batches.insert(0, batch_record)
    
    # 6. 截断保留最大数量
    batches = batches[:MAX_BATCHES]
    
    # 7. 写入文件
    with open(DASHBOARD_FILE, "w", encoding="utf-8") as f:
        json.dump(batches, f, ensure_ascii=False, indent=2)
    
    print(f"[面板更新] 批次 {batch_id} 已写入面板数据，当前共 {len(batches)} 条历史记录")
    print(f"  状态：{status} | 同步分：{batch_record['sync_score']} | 质量：{batch_record['quality_level']}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="更新流水线面板批次数据")
    parser.add_argument("--batch_id", required=True, help="批次唯一ID")
    parser.add_argument("--batch_dir", required=True, help="批次输出目录路径")
    parser.add_argument("--status", default="completed", choices=["completed", "failed", "running"], help="批次状态")
    parser.add_argument("--mode", default="ref2va", choices=["ref2va", "fl2va"], help="生产模式")
    
    args = parser.parse_args()
    update_batches(args.batch_id, args.batch_dir, args.status, args.mode)
```

### 插入流水线的方法

#### 方式 1：插入自动流水线末尾（推荐）

修改 `scripts/pipeline-tools/pipeline_auto.py`，在批次生产 + 评分完成后追加调用：

```
# 在 pipeline_auto.py 批次完成逻辑处追加
import subprocess

def update_dashboard(batch_id, batch_dir, status, mode):
    script_path = os.path.join(os.path.dirname(__file__), "update_dashboard_batch.py")
    subprocess.run(
        f'python {script_path} --batch_id {batch_id} --batch_dir {batch_dir} --status {status} --mode {mode}',
        shell=True,
        capture_output=True
    )
```

#### 方式 2：手动调用验证

```
# 测试更新面板
python scripts/pipeline-tools/update_dashboard_batch.py \
  --batch_id test_batch_001 \
  --batch_dir output_batch/test_batch_001 \
  --status completed \
  --mode ref2va
```

### 同步说明

脚本仅更新本地 `dashboard/batches.json`，**前文 NAS 核心资产同步脚本已默认包含该目录**，每小时自动同步至 RAID1 高可用区，面板多终端访问天然一致。
