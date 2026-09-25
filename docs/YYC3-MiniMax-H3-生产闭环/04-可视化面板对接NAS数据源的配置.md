---
file: 04-可视化面板对接NAS数据源的配置.md
description: 可视化面板对接 NAS 数据源配置（⚠️ batches.json 结构与仓库契约冲突，待 P1-C2 归一）
author: Intelligent Application Implementation Expert <admin@0379.email>
version: v1.1.0
created: 2026-09-25
updated: 2026-09-25
status: active
tags: [dashboard],[nas],[config],[blueprint]
category: config
language: zh-CN
changelog:
  - { version: v1.0.0, date: 2026-09-25, author: 智能应用落地专家, change: 原始版本收录（生成于外部会话） }
  - { version: v1.1.0, date: 2026-09-25, author: 智能应用落地专家, change: P1-D1 规范化（修复腐蚀链接/清理对话残留/补齐 YAML FM） }
---

# 可视化面板对接NAS数据源的配置

**100% 复用既有 A2A 消息基础设施、对齐 NAS 目录映射规范、匹配 H3 生产节点适配器协议**，可直接复制部署，零适配成本。

## 可视化面板对接 NAS 数据源配置说明

### 1.1 数据源架构与同步链路

完全对齐前文 NAS 目录映射规范，形成「生产端生成 → 增量同步 NAS → 多终端读取」的三级数据链路：

```
Mac 生产节点
    ↓ 每5分钟增量同步
NAS RAID1 高可用区：/volume1/RAID1/yyc3-core/h3-dashboard/batches.json
    ↓ HTTP / 本地文件读取
Ref2VA 流水线管理面板（dashboard/Ref2VA-流水线管理面板.html）
```

- **数据唯一事实源**：`batches.json`，由生产端批次脚本自动更新，包含所有批次的状态、参数、评分、耗时、资源占用等全量指标。
- **同步机制**：复用前文 `sync_h3_core_up.sh` 同步脚本，每 5 分钟增量同步至 NAS RAID1，双副本保障不丢失。
- **访问方式**：支持「本地文件模式」与「HTTP 服务模式」两种部署方式，适配不同使用场景。

### 1.2 两种部署模式配置

#### 1.2.1 本地文件模式（内网快速部署）

适合内网办公、单用户使用，直接读取本地挂载的 NAS 目录，零服务端部署。

1. **前置条件**：Mac/办公电脑已通过 SMB 挂载 NAS 共享目录，路径为 `/Volumes/YYC3-NAS/`。
2. **面板配置修改**：
   打开 `dashboard/Ref2VA-流水线管理面板.html`，找到文件头部的配置段：

   ```javascript
   // ==================== 数据源配置 ====================
   const CONFIG = {
       // 数据源地址：本地路径或 HTTP 接口
       dataSource: "/Volumes/YYC3-NAS/RAID1/yyc3-core/h3-dashboard/batches.json",
       // 自动刷新间隔（毫秒）
       refreshInterval: 300000,  // 5分钟，与NAS同步间隔对齐
       // 默认展示批次数量
       defaultShowBatches: 20
   };
   ```

3. **验证**：直接用浏览器打开 HTML 文件，面板自动加载 NAS 上的批次数据。

#### 1.2.2 HTTP 服务模式（多终端 / 公网访问）

适合团队共享、多终端访问、公网集成，通过 HTTP 服务暴露数据源，对齐 `api.0379.world` 网关规范。

**方案 A：NAS 端开启静态站点（推荐）**

1. 在 NAS 上创建静态站点，根目录指向 `/volume1/RAID1/yyc3-core/h3-dashboard/`。
2. 开启权限：只读，内网访问，绑定域名 `dashboard-h3.0379.world`。
3. 面板配置修改：

   ```javascript
   dataSource: "https://dashboard-h3.0379.world/batches.json",
   ```

**方案 B：DGX 端 Nginx 代理（复用现有网关）**

1. 在 DGX 节点 2 的 Nginx 配置中追加：

   ```nginx
   location /h3-dashboard/ {
       alias /mnt/nas/raid1-core/h3-dashboard/;
       autoindex on;
       add_header X-YYC3-Upstream "h3-dashboard";
   }
   ```

2. 面板配置修改：

   ```javascript
   dataSource: "https://api.0379.world/h3-dashboard/batches.json",
   ```

3. 优势：复用现有网关鉴权、限流、HTTPS 体系，无需额外服务。

### 1.3 面板核心功能与字段说明

`batches.json` 为标准数组结构，每个批次字段与 `manifest.json` 单一事实源一一对应：

| 字段 | 来源 | 说明 |
| ------ | ------ | ------ |
| `batch_id` | 批次名 | 唯一批次标识 |
| `create_time` | 生产时间 | 批次启动时间 |
| `mode` | 生产模式 | ref2va / fl2va |
| `input_text` | 口播文案 | 输入文本内容 |
| `ref_image` | 参考图 | 使用的数字人形象 |
| `num_frames` | 帧数 | 生成总帧数 |
| `total_time` | manifest | 总耗时（秒） |
| `avg_frame_time` | manifest | 单帧平均耗时 |
| `peak_memory` | manifest | 峰值内存占用（GB） |
| `sync_score` | score_lipsync | 口型同步评分（0-1） |
| `quality_level` | 综合评分 | 优秀/良好/合格 |
| `video_path` | 输出路径 | 视频文件相对路径 |
| `seed` | 生产参数 | 随机种子 |
| `status` | 运行状态 | completed / failed / running |

### 1.4 自动刷新与一致性保障

1. **生产端更新**：每批次生产完成后，自动更新本地 `dashboard/batches.json`，追加最新批次数据。
2. **NAS 同步**：每 5 分钟增量同步一次，确保 NAS 数据延迟不超过 5 分钟。
3. **面板刷新**：默认 5 分钟自动刷新一次，与同步间隔对齐，避免无效请求。
4. **一致性校验**：面板加载时校验数据哈希，发现更新自动刷新，无更新则使用本地缓存。

### 1.5 部署验证步骤

1. 生产一批测试视频，确认本地 `dashboard/batches.json` 已更新。
2. 手动执行一次同步脚本，确认 NAS 对应目录出现最新文件。
3. 打开面板，查看是否展示最新批次数据，各项指标是否正确。
4. 等待 5 分钟，验证自动刷新是否正常触发。

---

> 📌 关联文档：batches.json 生成见 [05-batches自动生成脚本.md](./05-batches自动生成脚本.md)（⚠️ 待 P1-C2 与 `export_dashboard_data.py` 契约归一）。
