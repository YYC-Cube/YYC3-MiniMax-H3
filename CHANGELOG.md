---
file: CHANGELOG.md
description: YYC3-MiniMax-H3 变更日志（Keep a Changelog 规范）
author: YanYuCloudCube Team <admin@0379.email>
version: v1.0.0
created: 2026-09-03
updated: 2026-09-27
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

### Changed

- **AI 助手网关实测通过（Phase 2B）**：0379-World 网关确认提供 OpenAI 兼容 LLM 端点（多后端代理：智谱 GLM/DeepSeek/Qwen/Llama 等 16 模型）——`GET /v1/models`（X-API-Key 与 Bearer 双通道 200）、`POST /v1/chat/completions` 非流式/流式（SSE + `yyc3-flush` 哨兵）契约达标；`createOpenAICompatible` 适配器零改动可用
  - 默认模型 `minimax-h3` → **`glm-4-flash`**（128k 上下文，实测往返正常）；`H3_LLM_API_KEY` 缺省复用 `H3_GATEWAY_API_KEY`（同一业务键双通道）
  - 端到端验证：工作台 `/api/chat` 输出 AI SDK v7 UIMessageStream（`text-delta` 逐字流式）；`/api/tasks` 带业务键 200
  - 新增部署 env 清单：docs/17-工作台部署环境清单.md + apps/console/.env.example（占位模板，真值 .secrets/ 隔离）

- **前端工作台迁移 Vite 6（apps/console 全量重构）**：Next.js 15 → **Vite 6 + React 19 + TS strict + Tailwind 4 + shadcn/ui + Zustand slice + Lucide + Motion + Vercel AI SDK v7**
  - 单端口架构：Hono BFF（`server/`）——dev 双进程（Vite 3030 代理 `/api` → API 127.0.0.1:3031，`scripts/dev.mjs` 编排）；prod 同进程托管 `/api` + `dist/` 静态 + SPA fallback（3030）
  - 服务端 lib 全量平移：`manifest`（/api/dashboard 取代 RSC fs 直读）/ `pipeline-manager`（spawn 白名单 + 环形日志 + fs.watch 文件总线 + SSE 回填/心跳）/ `gateway` / `api-auth`
  - 鉴权升级：新增 `/api/session` 短时会话令牌（HMAC-SHA256 12h，私网签发或 `H3_SESSION_KEY`，内存持有不落 URL——P1-S3 铁律延续）；令牌配置时全端点 fail-closed
  - 客户端：Zustand 四 slice（dashboard/pipeline/tasks/chat）+ 全 API/SSE 响应 zod 运行时校验（坏数据降级不崩 UI）+ 类型化 `createSSE`（命名事件/3s 重连/注销清理）
  - 页面：仪表盘（KPI/聚合卡/SVG 趋势/批次表）、流水线（SSE 日志台 + Motion 末行淡入 + memo 行）、任务中心（提交表单 8MB 预检 + blob 预览解决鉴权头注入）、批次详情精评抽屉（sonner 通知）、AI 助手（`/assistant`，useChat + streamText，0379-World OpenAI 兼容端点适配——**待 Phase 2B 网关实测**，env：`H3_LLM_BASE_URL/H3_LLM_API_KEY/H3_LLM_MODEL`，路由懒加载隔离 AI SDK 体积）
  - **Pages CI 转型**：h3.yyc3.top 由控制台快照 → **落地页/文档站**（`vite.landing.config.ts` → `dist-landing/`，曝光 + 预期管理 + 文档价值）
  - 验证：console build（vite + 双端 tsc）全绿；prod 冒烟 /api/health·dashboard·session·score·SSE·SPA fallback 全通；dev 双进程代理链路通（SSE 经 http-proxy 透传）；鉴权矩阵——远程无令牌 401 / 有效会话令牌放行 / 伪造拒收 / 回环直连
- **manifest 契约补强（性能字段 nullable）**：`recordSchema` 的 `gen_seconds/peak_rss_gb/mps_alloc_gb` 补 `.nullable()`——FAILED/中断记录写端初始为 null（batch1003 实证，同 lipsync 外层 nullable 先例）；`gen-json-schema.ts` 同步再生成；schema 冒烟测试 EXIT 0、双端契约同步 PASS

### Added

- **P2 任务闭环：面板 ↔ 网关队列全链路打通（/tasks 任务中心）**：实勘确认网关 Phase 2.3 任务闭环已存在（创建/列表/详情/下载 + claim/heartbeat/result/failure + 租约回收），唯一缺口是 console 零对接——本期补齐门面，不重造队列
  - 新增 4 个代理路由：`GET/POST /api/tasks`（列表/创建，LAN 直连规避公网链 90s 499 实证坑）、`GET /api/tasks/[id]`（轮询详情）、`GET /api/tasks/[id]/result`（mp4 流式代理）；task id 沿用 runner 白名单 `^[0-9a-f]{6,16}$` 防投毒；`/api/tasks/**` 鉴权 = `TASKS_CLAIM_TOKEN`（X-Claim-Token 常量时间比较）或未配置时 loopback
  - 新增 `lib/gateway.ts`（X-API-Key 仅存服务端）与 `lib/api-auth.ts`（共享鉴权）；**顺带补强 `/api/score` 零鉴权缺口**（写文件端点，GET/POST 双补，与 pipeline/run 同策略）
  - 新增 `/tasks` 页面：任务列表（四态徽章/重试次数/错误）+ 提交表单（prompt/quality/seed/参考图 base64）+ 10s 轮询 + succeeded 内嵌视频预览/下载
  - 验证：console build 全绿（4 路由+页面注册）；真网关 e2e 全链路——面板创建任务 `5d233e17d191` → `H3_FORCE=1` runner 干跑领取回报 → 面板详情 succeeded → result 代理流出合法 MP4（2.4MB）；score loopback 200 / 伪造 xff 401
- **僵尸批次终态收敛（TaskClear，借鉴数字人 ly_crontab 清扫器）**：修复 SIGTERM/崩溃后 `manifest.finish()` 未执行导致批次在面板永久 running 的缺口（实证：batch1000 seed10 于 08:00:53 被窗口截止杀死）
  - 新增 `scripts/pipeline-tools/reconcile_batches.py`：扫描 `ended_at=null` 的 manifest，以 `ps` 存活进程（`--batch N` 精确匹配）为唯一活跃判据；无进程则按 SUCCESS 记录数追加 `reconciled` 终态块（partial/failed + reason + retry_hint），不回改 `ended_at`（保留原始事实），先 `.bak-时间戳` 备份再原子写；默认 dry-run，`--apply` 执行、`--check` 供 CI、全程幂等（ps 异常时宁漏不误）
  - 契约扩展（`packages/manifest-schema`）：manifest 与 batches 单元新增可选 `reconciled` 块；批次状态机由 `completed|running` 扩为 **completed | running | partial | failed**（借鉴数字人 AiTaskEnum 五态终态语义）；`check_contract_sync.py` 字段清单同步至 18
  - 写端 `export_dashboard_data.py` 状态推导：收敛态优先 → 正常结束按失败 seed 分 partial/failed → 其余 running
  - 编排挂载：`nightly_run.sh` v1.2.0 新增 ③.5 收敛 stage（④ 面板刷新前）；另建议 08:10 独立 cron 兜底（安装行见脚本头注）
  - console：批次明细新增 ⚠ 部分完成 / ❌ 失败 徽章（hover 显示收敛时间与原因），聚合 KPI 改「完成 / 异常 / 运行」
  - 现场已收敛：batch1000→partial、batch998/999（09-26 白天空跑残留）→failed，各留 `.bak-20260927-111713` 可回滚

- **GB10 部署包情报整合**（源：NVIDIA 论坛社区部署包克隆，分析见 docs/12，对标清单 docs/13）：
  - 快预览档 `batch_ref2va_nf4.py --preview`（360p/64帧/30步，白天窗口快速迭代）+ `--variant` 参数化（nf4/pruned 切换，CUDA 侧绕过 bnb）
  - int8 黑屏自检纳入 docs/10 §5.2 杠杆 0 与 §8 验收清单（GB10 硅缺陷风险：到货首日 `steps=1` 检查，受影响锁 fp8）
  - docs/10 §5.2 增补低分辨率+超分杠杆（GB10 实测 6.03×）与统一内存带宽墙预案
- **docs/13-自研节点包对标清单.md**：上游 workflow JSON → zod 契约字段映射 + 8 个 custom node 功能对标（P1-P3 优先级）+ 节点包 v0.1 范围与验收门禁；Heretic 无审查 TE 划为合规红线永不纳管

- **Phase 2.1 归档通道**（`scripts/pipeline-tools/archive_to_nas.sh`）：双速制 NAS 归档（manifest 快车道实时 + 媒体慢车道 rsync -z 断点续传）、`.nas_pending` 降级队列 + `--retry-pending` 自愈补同步（对齐《第五能力审核论证》修正 1/3）
- **Phase 2.2 夜间批量**（`scripts/pipeline-tools/nightly_run.sh`）：22:00–08:00 窗口硬约束 + 全链路编排（生成→评分→归档→补同步→面板→次晨报告）+ `H3_FORCE` 调试逃生阀
- **docs/11-第五能力衔接实施方案.md**：三文档（DGX 指南/审核论证/可行性分析）收口 + Phase 2.3 异步任务 API 契约固化

### Fixed

- **SIGTERM 僵尸批次根修（batch_ref2va v1.2.0）**：09-27 batch1000 seed10 被定向 SIGTERM 杀死（扩散 41/50）后 manifest `ended_at=null`、面板永久 running——九个自动化嫌疑面穷尽排除后定性为窗口结束人为清场，真正缺口是被终止时系统不优雅。现装 SIGTERM/SIGINT 优雅处理器：in-flight seed 记 FAILED（半成品删除）、未起跑记 SKIPPED、`finally` 必写 `ended_at`、exit 143/130；异常路径同样收敛（SIGKILL/断电仍由 reconcile_batches 兜底）。面板状态机同步增强：`SKIPPED>0` 与 `FAILED>0` 同判 partial/failed。验证：真模块信号 E2E（GRACEFUL + exit 143）、状态机八分支 ALL_PASS、真实批次 export 零漂移
- **manifest 契约 lipsync 外层缺 nullable**：写端 `h3_common.add_record` 初始写 `lipsync: null`（评分前），zod schema 仅内层字段 nullable、外层对象未放行，导致未评分批次（batch1000）契约校验失败 → 外层补 `.nullable()`，7 个真实批次全绿
- **CI 供应链加固**：全部第三方 action 以 commit SHA 锁定（tag 可变、SHA 不可变，防 tag 劫持），同时消除 IDE「Unable to resolve action」报错
- **CI 红灯三连修 → 五门禁全绿**：
  1. pnpm 11 `minimumReleaseAge`（24h 供应链冷却）拒绝 lockfile 中当日发布版本（`@types/react-dom@19.2.7`、`postcss@8.5.27`）→ workspace `overrides` pin 到合规版本（8.5.26 / 19.2.5），安全策略不放松
  2. `ERR_PNPM_IGNORED_BUILDS: esbuild` → v11 已移除 `onlyBuiltDependencies`，构建许可迁移至 `allowBuilds: { esbuild: true }` 映射格式
  3. 契约测试在 CI 无 `output_batch*/` 生成数据时退出 1 → 无真实数据回退内置 fixture，门禁双端有效
- 配置收口：移除根 `package.json` 失效的 `pnpm` 字段，`pnpm-workspace.yaml` 归位为依赖设置单一真源

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
