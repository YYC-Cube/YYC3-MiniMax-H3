---
file: CHANGELOG.md
description: YYC3-MiniMax-H3 变更日志（Keep a Changelog 规范）
author: YanYuCloudCube Team <admin@0379.email>
version: v1.0.0
created: 2026-09-03
updated: 2026-10-05
status: active
tags: [changelog],[history],[release]
category: meta
language: zh-CN
changelog:
  - 2026-10-05 v1.0.1 FM 合规补全（补 changelog 字段，全局文档治理）
  - 2026-09-03 v1.0.0 初始版
---

# 变更日志

所有对本项目的显著变更将记录于此。
格式基于 [Keep a Changelog](https://keepachangelog.com/zh-CN/1.1.0/)，
版本遵循 [语义化版本 2.0.0](https://semver.org/lang/zh-CN/)。

## [Unreleased]

### Added

- **看门狗扩展件二连（docs/21 v1.1.0 · 告警钩子 + NAS 轮转归档）**：
  - **watchdog_alert_hook.py（告警钩子）**：告警纪律落地——指纹（模式:目标）+ 6h 静默窗口 + 连续 3 次升级（L1@3 提醒/L2@6 升级/L3@9 严重封顶）+ recovery 恢复通知；exit 2（线上抖动）不计数不通知防轰炸；三渠道独立降级（osascript 通知中心/H3_ALERT_WEBHOOK env/审计流 watchdog_alerts.jsonl）；**plist 链式升级**（探活→携退出码跑钩子，install_watchdog 重装生效）
  - **rotate_watch_jsonl.py（JSONL 轮转归档）**：主文件保留近 7 天（--keep-days/--dry-run）→ 按月切片 logs/archive/watch_YYYYMM.jsonl + rsync 幂等同步 NAS（yyc3-45:/Volume1/yyc3_hd/logs/watch/，不可达降级下次补传）；nightly_run.sh **④.7 挂载**；原子写防半行
  - **实测 TC-E1~E6 全绿**（docs/21 §4.1）：状态机全序（L1@3→4/5 静默→L2@6→exit2 不计数→recovery 清零；升级公式 `(n-1)//3+1`→`n//3` bug 修复实证）+ 轮转 dry-run/真跑/NAS **真实同步成功**/幂等 + 链式 launchd 全链（state 文件生成实证）

### Changed

- **智能化运维脚本闭环（docs/21 · B4 正式收口）**：
  - **install_watchdog.sh（看门狗一键安装器）**：launchd 用户域（gui/$UID）替代 setuid crontab 特权写——受限执行环境（沙箱/CI）可完成挂载；幂等（先卸后装）+ bootstrap/load 兼容回退 + `--status/--uninstall` 完整生命周期 + kickstart 试跑 JSONL 增长验证；前置自检退出码分级（exit 1 本地失败阻断 / exit 2 线上抖动放行——v1.0.0 曾误阻断已修）
  - **aggregate_watch_report.py（次晨聚合器）**：兑现 console_health_check「次晨报告可聚合」输出承诺——探测次数/模式分布/本地失败/agent 探活/P95 均值峰值+warn 聚合为 Markdown 段；nightly_run.sh **④.6 挂载**，坏行跳过不炸
  - **看门狗 agent 探点（P3）**：full 模式探 `AGENT_URL /api/healthz`（ok/claim_ready/transport 入 JSONL `record.agent`）；网关会话式常驻——`ok:false` 仅记录不判失败（零误报）；`--landing-only` 口径不变
  - **实测 8 用例全绿**（TC-O1~O8，docs/21 §四）：聚合器 8 行真数据/双模式回归/agent 正向/launchd 挂载回滚重挂/kickstart JSONL 14→15/exit2 分级实证——**launchd 挂载终态在位（600s 周期），无需设备前手工执行**
  - docs/21 编号入列（README 树/docs/05 地图/docs/09 矩阵三处同步，01~21 无缺号）
- **全局文档治理（2026-10-05 · 20 篇矩阵合规达标）**：
  - **FM 11 字段全库合规**：docs/01-07/09-15（9 篇）+ agent/API.md 补 `language`/`updated` 等缺项；README/CONTRIBUTING/SECURITY/agent-README 从零补齐全套 FM（YYC³ 文档硬约束闭环）
  - **编号化入列**：非编号论证文档 → `docs/19-第五能力审核论证.md`（docs/11 拍板依据）+ `docs/20-结构衔接可行性分析.md`（原方案准源）——引用全为书名号级零破坏，git 识别 rename 历史保留
  - **徽章系统完善（README v2.5.0）**：新增 CI/Pages Deploy 实况徽章 + Workbench 栈徽章（React19·Vite6·Hono）；Version 徽章 v2.2.0→v2.5.0 对齐变更史；Docs 徽章 10+→20_Guides；目录树补 19/20 + 双 HTML 角色注释 + vendor/dgxspark 克隆来源注释
  - **文档矩阵三处同步**：docs/05 §四 文档地图 07→20 号、docs/09 §1.1 矩阵 09→20 号 + §1.2 审核结论复审（01~20 无缺号/FM 全合规）、README 目录树
  - **一致性修正**：agent 冒烟用例数 12→17 三处（README/docs/08 §10.2/CONTRIBUTING）
  - **活文档刷新**：docs/06 §1.0.3 工程快照（漫剧 P0-P2 落地/工作台/门禁/供应链）+ §五 TOP3 刷新（A 系列闭环 → B4 cron 挂载/B5 视觉验证/治理常态化）
  - **git 卫生**：.gitignore 补 `vendor/DiffSynth-Studio/`（引擎克隆，对齐 dgxspark 先例）+ `projects/` + `.nas_pending/`（agent/NAS 运行时态）——git status 清零 untracked 噪音
- **供应链加固收口：GitHub Actions 引用全量 commit SHA 锁定（ci.yml + pages.yml 共 9 处）**：pnpm/action-setup→`a7487c7`（v4.1.0）/setup-node→`49933ea`（v4.4.0）/upload-pages-artifact→`56afc60`（v3.0.1）/deploy-pages→`d6db901`（v4.0.5），与既有 checkout/setup-python 对齐——补齐「tag 可变→SHA 不可变」供应链纪律的声明缺口（grep 复核零 tag 残留）
- **分镜闸门文档/env 对齐 + E2E 复验（docs/18 P1 收尾）**：docs/08 升 **v1.4.0**（§3.3 补 `/api/storyboard` 四端点行 + agent 网关侧映射 + §1.3 架构图补分镜代理行）；docs/17 §2.4 与 console `.env.example` 补 `H3_AGENT_URL` 运行参数；闸门 curl 全链复验通过——submit→`waiting_feedback`→confirm（dry_run+preview）→生产官 argv 含 `--dry-run --preview` →质检结构化降级 verdict=blocked/manifest_missing（非 500）；无 claim 负路径 401 fail-closed。遗留登记：①浏览器视觉验证待本机执行；②看门狗 cron 挂载因沙箱阻断 crontab 特权写（setuid 进程 3 次挂死），待设备前按 docs/17 §5.3 命令手动执行
- **AI 漫剧/短剧功能演进方案（docs/18 v1.0.0）**：基于 MiraFrame/OnlyShot 双仓库实勘（gh api 交叉验证）+ 同类横向检索（ArcReel 5.2k★/Toonflow 10k+★/BigBanana；修正 Toonflow 协议为 AGPL-3.0）——适配矩阵 15 项判定（✅4 同构互证/🔧5 补强/➕3 新建/⛔3 不采纳附因）；确立**双层一致性**差异化定位（Ref 控身份 × seed 控稳定，行业独有）；演进路线 P0（契约扩展 video_mode/asset_ref/pacing + Ref 资产库结构化）→ P1（编排器第六态 waiting_feedback + console 分镜确认闸门 + 失败模式结构化）→ P2（首尾帧插值探测 + 分级生成策略）；含 Mermaid 全景流程图/闸门时序/依赖序三图
- **B2 漫剧 E2E 实测通过 + dry_run 透传事故根修（agent 网关）**：本机 h3-m4 实测 agent 网关全链（8300 启动 → 三 Agent 注册 → CLI claim 签发 → POST /api/tasks generate_batch dry_run）——首测暴露 🔴 `TaskRequest` 顶层 `dry_run` 被 pydantic 静默丢弃 → 生产官真实 spawn `pipeline_auto --batch 99 --auto`（即时止损：0 视频产物、误建 output_batch99/report 清理、git 零污染）；根修 = 快捷字段声明并入 + `merge_task_payload` 纯函数抽出 + **3 用例防回归**（test_smoke 12→**15**）；复测 argv=`--batch 99 --auto --dry-run` 秒回 completed。CI 核心回归同步装 fastapi（gateway 测试依赖，不装 redis 保 InMemory）。实测记录固化 docs/17 §5.4
- **看门狗增强（--landing-only）**：纯线上 TTFB P95 观测模式（BFF 按需启动时 cron 零误报）；基线采样 P95 = 1.94/2.59/1.96s（远低于 warn 阈 5s，无需 CDN 动作）；docs/17 §5.3 更新双模式用法
- **终审遗留五项落地（P2×3 + P3×2）**：
  - **路由全量懒加载**：Pipeline/Tasks/BatchDetail 与 AI 助手同列按需 chunk（页面级 ×5）——主包 382→359KB（gzip 114→108KB），Dashboard 首屏 eager 保 TTFB
  - **工作台看门狗**（`scripts/pipeline-tools/console_health_check.py`）：探活矩阵 = BFF health + SSE 首事件 + 线上 TTFB P95 采样（5 样本），JSONL 落 `logs/console_watch.jsonl` 供次晨报告聚合；退出码 0/1/2（在线全过/本地探活失败/仅线上抖动）——实测在线 exit 0（health 14ms·SSE 2ms·P95 2.2s）、离线 exit 1 ✓；cron 接入行见 docs/17 §5.3
  - **Pages 灰度通道**：pages-deploy `workflow_dispatch` 新增 `ref` 输入（任意分支/commit 预发验证部署）——静态原子切换的灰度替代 SOP + 四通道回滚表落 docs/17 §五
  - **B2 漫剧 E2E 接线清单**：docs/17 §六固化（env 双变量 + runner 心跳前置 + 验收链五步）；本机现状：`agent_claim.env` 在位、`H3_AGENT_GATEWAY` 待接线（真机触发）
  - **线上 TTFB 抖动观测**：纳入看门狗 P95 基线（warn 阈 5s，只记录不告警）——数据驱动后续 CDN 决策
- **开发者文档对齐实况 + 开源五件套补全**：docs/08 升 v1.3.0——新增 §1.3 可视化与工作台层架构图（Vite SPA/Hono BFF/agent/dashboard/落地页全景）、§2.4 前端快速上手（pnpm dev/build/start/landing 四命令）、§3.3 工作台 BFF HTTP API（11 端点 + 鉴权矩阵 + zod 消费契约）；§9 索引补 16-17 与 console/agent 代码入口；§10 门禁由五项扩为六项（新增前端构建门禁）；FM 补 language/changelog。**CONTRIBUTING 同步**（pnpm 环境 + 前端门禁 + SECURITY 链接）；**新增 SECURITY.md**（漏洞报告渠道/支持版本/安全范围/密钥纪律/加固基线）——根目录开源五件套（README·LICENSE·CONTRIBUTING·CHANGELOG·SECURITY）齐备
- **AI 助手网关实测通过（Phase 2B）**：0379-World 网关确认提供 OpenAI 兼容 LLM 端点（多后端代理：智谱 GLM/DeepSeek/Qwen/Llama 等 16 模型）——`GET /v1/models`（X-API-Key 与 Bearer 双通道 200）、`POST /v1/chat/completions` 非流式/流式（SSE + `yyc3-flush` 哨兵）契约达标；`createOpenAICompatible` 适配器零改动可用
  - 默认模型 `minimax-h3` → **`glm-4-flash`**（128k 上下文，实测往返正常）；`H3_LLM_API_KEY` 缺省复用 `H3_GATEWAY_API_KEY`（同一业务键双通道）
  - 端到端验证：工作台 `/api/chat` 输出 AI SDK v7 UIMessageStream（`text-delta` 逐字流式）；`/api/tasks` 带业务键 200
  - 新增部署 env 清单：docs/17-工作台部署环境清单.md + apps/console/.env.example（占位模板，真值 .secrets/ 隔离）
- **前端工作台迁移 Vite 6（apps/console 全量重构）**：Next.js 15 → **Vite 6 + React 19 + TS strict + Tailwind 4 + shadcn/ui + Zustand slice + Lucide + Motion + Vercel AI SDK v7**
  - 单端口架构：Hono BFF（`server/`）——dev 双进程（Vite 3030 代理 `/api` → API 127.0.0.1:3031，`scripts/dev.mjs` 编排）；prod 同进程托管 `/api` + `dist/` 静态 + SPA fallback（3030）
  - 服务端 lib 全量平移：`manifest`（/api/dashboard 取代 RSC fs 直读）/ `pipeline-manager`（spawn 白名单 + 环形日志 + fs.watch 文件总线 + SSE 回填/心跳）/ `gateway` / `api-auth`
  - 鉴权升级：新增 `/api/session` 短时会话令牌（HMAC-SHA256 12h，私网签发或 `H3_SESSION_KEY`，内存持有不落 URL——P1-S3 铁律延续）；令牌配置时全端点 fail-closed
  - 客户端：Zustand 四 slice（dashboard/pipeline/tasks/chat）+ 全 API/SSE 响应 zod 运行时校验（坏数据降级不崩 UI）+ 类型化 `createSSE`（命名事件/3s 重连/注销清理）
  - 页面：仪表盘（KPI/聚合卡/SVG 趋势/批次表）、流水线（SSE 日志台 + Motion 末行淡入 + memo 行）、任务中心（提交表单 8MB 预检 + blob 预览解决鉴权头注入）、批次详情精评抽屉（sonner 通知）、AI 助手（`/assistant`，useChat + streamText，0379-World OpenAI 兼容端点适配，路由懒加载隔离 AI SDK 体积）
  - **Pages CI 转型**：h3.yyc3.top 由控制台快照 → **落地页/文档站**（`vite.landing.config.ts` → `dist-landing/`，曝光 + 预期管理 + 文档价值）
  - 验证：console build（vite + 双端 tsc）全绿；prod 冒烟 /api/health·dashboard·session·score·SSE·SPA fallback 全通；dev 双进程代理链路通（SSE 经 http-proxy 透传）；鉴权矩阵——远程无令牌 401 / 有效会话令牌放行 / 伪造拒收 / 回环直连
- **manifest 契约补强（性能字段 nullable）**：`recordSchema` 的 `gen_seconds/peak_rss_gb/mps_alloc_gb` 补 `.nullable()`——FAILED/中断记录写端初始为 null（batch1003 实证，同 lipsync 外层 nullable 先例）；`gen-json-schema.ts` 同步再生成；schema 冒烟测试 EXIT 0、双端契约同步 PASS
- **工作台品质闭环（③可访问 + ④性能）**：可访问——原生 select/checkbox 焦点环与 label 关联强化、AI 助手输入框 label 关联、任务视频 aria-label、SSE 徽章装饰点 aria-hidden；性能——vite manualChunks 稳定 vendor 拆分（react/motion/virtual），主包降至 500KB 以下、批次明细表 `@tanstack/react-virtual` 窗口化（sticky 表头 + overscan 8）；docs/16 增补 ADR-FE-002 栈变更记录（Next.js→Vite 决策定稿）

### Fixed

- **终审整改：CI 核心回归空集根修**——原门禁命令 `unittest discover scripts/pipeline-tools` 实为 0 用例（全仓唯一测试集在 `agent/tests/test_smoke.py` 12 用例，此前 CI 从未执行任何 Python 单测）。ci.yml 新增「核心回归（agent 冒烟 12 用例）」步骤（working-directory: agent）；docs/08 §10.2 与 CONTRIBUTING 门禁命令同步纠正
- **CI 供应链冷却补 pin（hono 4.13.13 <24h 被拒）**：pages-deploy 在 `pnpm install --frozen-lockfile` 阶段被 pnpm 11 `minimumReleaseAge` 拦截（hono@4.13.13 于 2026-10-04 发布，距 CI 运行不足 24h）——workspace overrides 追加 `hono: 4.13.12`（09-30 发布，功能等价），本地 frozen 复验通过
- **gitignore 否定失效修复（batches.json git add 失败）**：`dashboard/data/` 目录排除在路径遍历层剪枝，使 `!dashboard/data/batches.json` 无法重新包含；另裸 `data/` 模式命中任意层级（含 dashboard/data）。改为 `dashboard/data/*`（只排除内容）+ `/data/` 根锚定——batches.json 恢复免 `-f` 正常 add，根 data/ 与其他 dashboard 数据仍隔离

### Added

- **演进路线 P1+P2 全量落地（docs/18 §八执行记录，同日交付）**：
  - **P1-1 分镜确认闸门**：`StageStatus` 第六态 `waiting_feedback`（上游五态契约不动）+ 编排器 `submit_storyboard`（候选 1-4 张/路径穿越防护/批次白名单）→ `confirm_storyboard`（selected∈候选集 → asset_ref → 复用阶段4 闭环）+ 网关三端点（confirm 默认 dry_run 安全默认）；test_smoke 15→**17**（六态全链 + 四类约束拒绝）
  - **P1-2 console 分镜确认页**：BFF `/api/storyboard` 三端点（代理 agent 网关，claim 头透传 + authorizePipeline 双层门禁）+ 候选图静态 `/api/storyboard/ref/*`（穿越防护）；前端 `/storyboard`（9:16 候选网格 radiogroup 单选 → 档位选择 + 演练默认勾选 → 确认触发；导航"分镜确认"入口）
  - **P1-3 失败模式结构化**：契约 `record.reason` 七值枚举（optional 兼容）；写端三处（add_record 条件附加/SIGTERM→sigterm/种子级 except→model_error）；面板批次详情失败记录区（reason 中文徽章）；nightly ④.5 reason+video_mode 分布统计入次晨报告
  - **P2-1 首尾帧插值探测（结论可行）**：vendor `minimax_h3_audio_video.__call__` 实勘——`keyframes+keyframe_indices`（官方约束 {0,-1}）= **首尾帧原生支持**，`video_mode:"frames"` 引擎封装透传即启用；>2 帧当前版本不支持；**额外发现 `retake_video` 局部重拍能力**（后续独立评估）
  - **P2-2 分级生成**：`confirm_storyboard(quality=)` → 生产官 payload → `pipeline_auto --preview`（新增参数）→ batch 脚本快预览档；E2E 修出两边界：rework 打回循环丢失 quality（已根修保留档位）、无产物批次质检 500（已改结构化降级 verdict=blocked+reason=manifest_missing）
  - **E2E 全链实证**（console BFF→agent 网关）：submit→waiting_feedback→confirm(dry_run+preview)→argv=[--batch,97,--auto,--dry-run,**--preview**]+asset_ref+qc.reason ✓；无 claim 写操作 401 ✓；17 用例/console build/schema 回归全绿
- **演进路线 P0 落地（docs/18 §四：契约扩展 + Ref 资产库结构化）**：
  - **P0-1 manifest 契约扩展**：`recordSchema` 增 `video_mode`（枚举 ref2va/fl2va/frames——frames 为首尾帧插值预留，P2-1 探测后启用写端）/ `asset_ref`（Ref 资产关联）/ `pacing`（节奏元数据回传位），全部 optional 向后兼容（15 真实批次回归零影响）；JSON Schema 再生成 +14 行漂移一致
  - **P0-2 Ref 资产库结构化**：新增 `packages/manifest-schema/src/assets.ts`（assetsManifest 契约：characters/scenes/props 三类，id/kind/name/files/tags，BigBanana 衣橱思路 tags 对位）；`organize_ref_assets.py` 迁移脚本（dry-run 默认/幂等/结构自检，实测 person_a → characters/ 入位 + assets.json 清单生成）
  - **引擎适配（关键兼容修复）**：`batch_ref2va_nf4.py` 参考图扫描 `os.listdir` 顶层 → `rglob` 递归（资产库三类子目录可直接被引擎消费；ref_img 记录相对路径含子目录前缀，report/score 写回链路一致）
  - test-schema 增 3 fixture（演进字段通过/非法 video_mode 拒绝/资产清单契约）；契约同步门禁/console build 全绿
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
