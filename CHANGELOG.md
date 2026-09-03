---
file: CHANGELOG.md
description: YYC3-MiniMax-H3 变更日志（Keep a Changelog 规范）
author: YanYuCloudCube Team <admin@0379.email>
version: v1.0.0
created: 2026-09-03
updated: 2026-09-03
status: active
tags: [changelog],[history],[release]
category: meta
language: zh-CN
---

# 变更日志

所有对本项目的显著变更将记录于此。
格式基于 [Keep a Changelog](https://keepachangelog.com/zh-CN/1.1.0/)，
版本遵循 [语义化版本 2.0.0](https://semver.org/lang/zh-CN/)。

## [Unreleased]

### Fixed

- **CI 红灯修复**：pnpm 11 `minimumReleaseAge` 供应链冷却策略拒绝 lockfile 中当日发布版本（`@types/react-dom@19.2.7`、`postcss@8.5.27`）→ workspace `overrides` pin 到合规版本（8.5.26 / 19.2.5），保留安全策略不放松
- 配置收口：移除根 `package.json` 失效的 `pnpm` 字段与 `pnpm-workspace.yaml` 脏占位符（`allowBuilds`），`onlyBuiltDependencies` 归位 workspace 单一真源

### Added

- **路线B 生产控制台**（`apps/console/`，Next.js 15 + pnpm workspace）
  - `/` 仪表盘：RSC 直读 `output_batch*/manifest.json` 单一事实源，评分趋势/缺陷分布/Seed 对比/缺陷趋势四图（ECharts）
  - `/pipeline` 流水线控制：触发 API + SSE 实时日志台（回填 300 行、15s 心跳、3s 断线重连）
  - `/batches/batchXX` 批次详情：视频卡片网格 + 人工精评抽屉（1~10 滑条 + 缺陷标签）
  - `/api/score`：按 `参考图+Seed` 定位写回 `report_batchXX.md`，完成后静默刷新数据桥
- **manifest 变更自动刷新**：`fs.watch` 递归监听 → 500ms 去抖 → SSE `file` 事件 → `router.refresh()` 无感更新
- **双端 schema 契约**（路线C 契约层，`packages/manifest-schema/`）
  - zod 唯一真源 → `gen-json-schema.ts` 生成 Draft-07 JSON Schema
  - `validate_manifest.py` Python 端校验器（jsonschema 可选，缺失降级结构快检）
  - zod / Python 双端互验通过（真实 batch01 数据）
- **CI 门禁**（`.github/workflows/ci.yml`）：Python 编译 → 契约校验 → schema 漂移检查 → console 构建 → spawn 白名单完整性
- 静态管理面板（`dashboard/`，路线A 数据桥）：fetch `dashboard/data/batches.json`，失败自动降级模拟数据
- `export_dashboard_data.py`：manifest → `batches.json` 聚合层（评分 0-10 统一刻度、缺陷标签聚合、Top10）
- `pipeline_auto.py` CLI：`--batch/--auto/--dry-run`（非交互触发与联调演练），步骤⑤' 自动刷新面板数据
- GitHub 仓库标签体系 v2.0（topics ×10 三层词表：品牌/领域/引擎·平台·生态）

### Changed

- `packages/manifest-schema`：补写端扩展字段（`time/mps_alloc_gb/backend/scored_at`）+ `.passthrough()` 扩展放行
- 文档/代码标头标尾全量规范化（22 py + 15 md，YYC³ FM + 品牌标尾 + 变更历史）
- 根目录整理：源文档归档 `docs/legacy/`，品牌资产 `docs/assets/`，DiffSynth 转 submodule（锁 `b6b279d`）

### Fixed

- `pipeline_auto.py` 四处脚本引用路径错位（`SCRIPTS_DIR/TOOLS_DIR` 锚定）
- `pipeline_auto.py` 非交互 EOF 崩溃（`--auto` 跳过 `input()`）
- 多 lockfile 环境 `outputFileTracingRoot` 误推断（`next.config.ts` 显式锚定）
- Tailwind v4 简写迁移 ×31（`[var(--x)]` → `(--)`）

## [v2.0.0] - 2026-09-02

### Added

- MiniMax-H3 NF4 量化本地推理（Apple M4 Max 128GB 实测基线：≥3.3 it/s、RSS ~32.8GB）
- Ref2VA 端到端流水线：参考图 + 语音 → 说话视频（身份保持）
- SyncNet 自动口型评分 + 启发式降级
- `manifest.json` 双向数据契约（生成侧写、消费侧读）
- 性能基线采集（RSS / MPS 峰值）与批次报告体系

[Unreleased]: https://github.com/YYC-Cube/YYC3-MiniMax-H3/compare/v2.0.0...HEAD
[v2.0.0]: https://github.com/YYC-Cube/YYC3-MiniMax-H3/releases/tag/v2.0.0

---

> 「***YanYuCloudCube***」
> 「***<admin@0379.email>***」
> 「***Words Initiate Quadrants, Language Serves as Core for the Future***」
> 「***All things converge in cloud pivot; Deep stacks ignite a new era of intelligence***」

## 变更历史

| 版本 | 日期 | 作者 | 变更内容 |
| ---- | ---- | ---- | -------- |
| v1.0.0 | 2026-09-03 | YanYuCloudCube Team | 初始版本：收录 v2.0.0 发布基线 + 路线A/B/C 落地记录 |

**© 2025-2026 YanYuCloudCube™. All Rights Reserved.**
