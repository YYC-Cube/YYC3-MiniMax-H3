---
file: SECURITY.md
description: YYC3-MiniMax-H3 安全策略——漏洞报告渠道、支持版本、安全范围与密钥纪律
author: YanYuCloudCube Team <admin@0379.email>
version: v1.1.0
created: 2026-09-26
updated: 2026-10-05
status: active
tags: [security],[policy],[vulnerability]
category: meta
language: zh-CN
changelog:
  - 2026-10-05 v1.1.0 FM 合规补全（11 字段，YYC³ 硬约束）
  - 2026-09-26 v1.0.0 初始版（漏洞渠道/支持版本/密钥纪律/加固基线）
---

# 安全策略（Security Policy）

> YanYuCloudCube · YYC3-MiniMax-H3。本仓库以 MIT 许可开源；安全纪律继承「生产闭环」治理蓝图（docs/YYC3-MiniMax-H3-生产闭环/）。

## 支持版本

| 版本 | 支持状态 |
| ---- | ---- |
| main（最新提交） | ✅ 支持 |
| 历史标签 | ❌ 请升级到 main |

## 报告漏洞

- **渠道**：admin@0379.email（私下报告，勿开公开 issue）
- **响应时效**：72h 内确认收悉；P0 级 7 天内出缓解方案
- **请附**：影响范围、复现步骤/POC、受影响文件路径；我们会在修复后公开致谢（除非你要求匿名）

## 安全范围

| 范围 | 说明 |
| ---- | ---- |
| Python 引擎（scripts/） | spawn/argv 注入、路径穿越、产物完整性 |
| 工作台 BFF（apps/console/server/） | 鉴权旁路、SSE/代理端点滥用、spawn 白名单绕过 |
| 契约（packages/manifest-schema/） | 校验绕过导致的注入面 |
| 网关交互（0379-World） | 仅服务端持钥；客户端密钥泄露属网关侧策略 |

不在范围：无凭据的 DoS、纯理论问题、社交工程。

## 密钥纪律（开源红线）

- 一切密钥走环境变量：`.env`（不入库，`.env.example` 为占位模板）/ `.secrets/`（本机隔离，600 权限，已 gitignore）
- 文档/代码中密钥一律 `${ENV_VAR}` 占位——曾发生的历史明文泄露已按「吊销 + 轮换 + 哈希比对实证」处置（见 CHANGELOG 2026-09-26 条目）
- **严禁** URL 查询参数传密钥（P1-S3 铁律）；远程访问走短时会话令牌（`/api/session`，HMAC 12h）

## 已知加固措施（贡献者自查基线）

- 子进程一律 argv 数组注入（禁 `shell=True` 拼接用户输入）；流水线 spawn 白名单仅 `pipeline_auto.py`
- 网关写操作令牌常量时间比较（`timingSafeEqual`）；task id 白名单 `^[0-9a-f]{6,16}$` 防队列投毒
- CI 供应链：第三方 action 以 commit SHA 锁定；pnpm `minimumReleaseAge` 24h 冷却 + overrides pin
- 部署 env 清单与密钥真源映射：[docs/17-工作台部署环境清单](docs/17-工作台部署环境清单.md)

---

> 「***YanYuCloudCube***」· admin@0379.email
> **© 2025-2026 YanYuCloudCube™. All Rights Reserved.**
