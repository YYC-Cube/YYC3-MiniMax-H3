---
file: 22-CDN接入SOP.md
description: h3.yyc3.top 线上加速 Cloudflare 接入标准作业程序——诊断证据、选型、分步执行、验证、回滚与执行记录表
author: YanYuCloudCube Team <admin@0379.email>
version: v1.0.0
created: 2026-10-05
updated: 2026-10-05
status: active
tags: [cdn],[cloudflare],[ops],[ttfb],[sop]
category: guide
language: zh-CN
changelog:
  - 2026-10-05 v1.0.0 初始版：由 docs/17 §七扩展为独立执行级 SOP（选型对比/重定向陷阱/缓存规则/执行记录表）
---

# 🌐 CDN 接入 SOP（h3.yyc3.top）

> **目标**：将线上落地页 P95 TTFB 从均值 4.69s/峰值 18.6s（跨境 TLS 握手抖动）收敛至 **<3s 稳态**。
> **执行人**：域名管理员（admin@0379.email）｜**预计耗时**：30 分钟｜**回滚耗时**：<5 分钟（DNS TTL）。

---

## 一、诊断证据（2026-10-05 已固化，接入后同源对比用）

| # | 证据 | 数值 | 含义 |
| - | ---- | ---- | ---- |
| 1 | 看门狗 110 有效样本 | p50=2.16s · p90=17.1s · **≥10s 慢尾 15 个（14%）** | 慢尾主导 P95，中位数其实健康 |
| 2 | curl 阶段分解 ×3 | round3：`dns=0.005s` **`tls=11.0s`** `ttfb=11.13s` | **瓶颈 99% 在 TLS 握手**——非 DNS、非首字节、非页面 |
| 3 | DNS 解析 | `h3.yyc3.top → yyc-cube.github.io → 185.199.108-111.153` | 跨境直连 GitHub Pages，无近端前置 |
| 4 | 落地页体积 | dist-landing 共 **1.8MB**（index.html 727B，assets 带 hash） | 页面无辜——资源优化不是本题解 |

**结论**：客户端到 GitHub Pages 边缘的跨境 TLS 握手抖动。CDN 近端终止 TLS 是唯一对症解。

**接入前基线留存**（执行 §五 验证前先跑一次并截图/保存输出）：

```bash
for i in 1 2 3 4 5; do curl -s -o /dev/null -m 20 -w "dns=%{time_namelookup} tls=%{time_appconnect} ttfb=%{time_starttransfer} http=%{http_code}\n" https://h3.yyc3.top; done
/opt/miniconda3/envs/h3-m4/bin/python scripts/pipeline-tools/aggregate_watch_report.py
```

---

## 二、方案选型

| 方案 | 费用 | 优点 | 顾虑 | 判定 |
| ---- | ---- | ---- | ---- | ---- |
| **Cloudflare 免费版（NS 接入）** | ¥0 | 无限流量 CDN、全球节点、SSL Full(strict)、5 分钟生效回滚 | 国内无备案节点（走香港/新加坡/美西——**但 TLS 终止在近端节点后，跨境段收敛为 CF 骨干**，对本病例有效） | ✅ **主案** |
| 腾讯云 EdgeOne 个人版 | ¥0 限量 | 国内节点、速度最优 | 需域名备案（yyc3.top 备案状态未确认）+ 实名 | 备案齐备后的升级选项 |
| 不接 CDN | — | 零变更 | P95 维持 4-5s，warn 持续累积 | 已被诊断证据否决 |

> 免费版需 **NS 全站接入**（子域级 CNAME 代理为付费功能）；yyc3.top 下其他子域的 DNS 记录需在接入时照搬（§四 步骤 2 有防丢核查）。

---

## 三、前置检查清单（逐项确认后才开始）

- [ ] 域名 `yyc3.top` 管理权限（注册商后台可改 NS）
- [ ] 盘点 yyc3.top 现有全部 DNS 记录（`dig yyc3.top ANY` + 注册商后台导出/截图——**NS 切换后记录要在 Cloudflare 重建，漏一条断一个服务**）
- [ ] GitHub Pages 现状：`public/CNAME` = `h3.yyc3.top`（仓库已配置，无需变更）
- [ ] 本 SOP §一 基线已留存
- [ ] 回滚预案通读（§六——出错 5 分钟内可恢复直连）

---

## 四、接入步骤（Cloudflare 免费版）

### 步骤 1：添加站点
Cloudflare 控制台 → Add a site → `yyc3.top` → Free 计划 → 扫描既有 DNS 记录。

### 步骤 2：核对/补全 DNS 记录（防丢关键步）
对照步骤三盘点清单逐条核对，Cloudflare 未扫到的手动补建。本仓库相关记录：

| 类型 | 名称 | 目标 | 代理状态 |
| ---- | ---- | ---- | ---- |
| CNAME | `h3` | `yyc-cube.github.io` | **已代理（橙色云）** ← 加速开关 |

其余子域记录照搬（代理状态默认**仅 DNS 灰云**，除非明确要加速——最小变更原则）。

### 步骤 3：切换 NS
按 Cloudflare 提示到注册商后台将 NS 改为 Cloudflare 分配的两个地址 → 回控制台点 **Check nameservers**（生效 5 分钟-24h，通常 <30 分钟）。

### 步骤 4：SSL/TLS 配置（⚠ 顺序与模式是最大坑）
1. 等 NS 生效（状态 Active）后进入 **SSL/TLS → Overview**
2. 模式选 **Full (strict)**（回源 GitHub Pages 证书有效）
   > ⚠️ **绝不可选 Flexible**：GitHub Pages 侧已开 Enforce HTTPS，Flexible 会造成 **无限重定向循环**（301 loop）——这是本 SOP 唯一的硬故障模式
3. SSL/TLS → Edge Certificates → 开启 **Always Use HTTPS**

### 步骤 5：缓存规则（落地页部署即时可见）
Rules → Cache Rules 新建：

| 规则 | 匹配 | 行为 |
| ---- | ---- | ---- |
| index 绕过 | `h3.yyc3.top/index.html` 或 URI Path equals `/` | **Bypass cache**（Pages 每次部署即时可见） |
| assets 长缓存 | URI Path starts with `/assets/` | Edge TTL 1 个月（文件名带 content hash，天然免失效） |

### 步骤 6：（可选）速度优化
Speed → Optimization → 开 Brotli（默认开）；**勿开 Rocket Loader/Mirage**（对纯静态落地页无益且可能干扰脚本执行）。

---

## 五、验证与通过标准

NS 生效后执行（与 §一 基线同源可比）：

```bash
# ① 阶段分解 ×5：tls 应 <0.3s（基线 0.7-11s）、http=200、无 3xx 循环
for i in 1 2 3 4 5; do curl -s -o /dev/null -m 20 -w "dns=%{time_namelookup} tls=%{time_appconnect} ttfb=%{time_starttransfer} http=%{http_code}\n" https://h3.yyc3.top; done

# ② DNS 解析应指向 Cloudflare 节点（104.x/172.x 段），不再是 185.199.x
dig +short h3.yyc3.top | head -4

# ③ 看门狗同源观测：持续观察 24h（nightly ④.6 次晨报告自动聚合）
/opt/miniconda3/envs/h3-m4/bin/python scripts/pipeline-tools/aggregate_watch_report.py
```

| 验收项 | 通过标准 |
| ---- | ---- |
| TLS 握手 | <0.3s（5 轮全过） |
| TTFB | <1.5s 常态 |
| 看门狗 P95（24h 后） | **<3s 且 warn=0** |
| HTTP 状态 | 200，无重定向循环 |
| 落地页内容 | 与直连一致（浏览器打开核对） |

任一不满足 → 直接执行 §六 回滚，回滚后排障（勿在半接入态滞留超过 30 分钟）。

---

## 六、回滚（<5 分钟）

1. 注册商后台：NS 改回原注册商默认 NS（步骤三盘点记录仍在原处则即刻恢复）
2. 若原 DNS 已删：按盘点清单重建 `h3 → yyc-cube.github.io` CNAME（或 A 记录四条 `185.199.108/109/110/111.153`）
3. 验证：`dig +short h3.yyc3.top` 回到 `185.199.x` + curl 200
4. 回滚后在本文 §八 执行记录表登记原因，重新评估 EdgeOne 备案路径

---

## 七、风险与影响评估

| 风险 | 评估 | 缓解 |
| ---- | ---- | ---- |
| 无限重定向循环 | 唯一硬故障（Flexible 模式触发） | §四步骤 4 强制 Full(strict)；验证发现 3xx 循环立即回滚 |
| 其他子域 DNS 丢失 | NS 切换操作面大 | §三盘点 + §四步骤 2 逐条核对，**先建全记录再切 NS** |
| Pages 新部署不刷新 | CDN 缓存 index | §四步骤 5 index Bypass 规则 |
| Cloudflare 国内可达性波动 | 免费版无中国节点 | TLS 已近端终止，跨境段走 CF 骨干优于公网直连；若 24h 观测不达标可回滚转 EdgeOne |
| CI/CD 影响 | 无——GitHub Pages 部署链路不变，仅 DNS 前置层变化 | — |

---

## 八、执行记录表（接入后回填）

| 项 | 值 |
| ---- | ---- |
| 执行人 / 日期 | ＿＿＿＿ / ＿＿ |
| NS 切换时间 | ＿＿ |
| Cloudflare 生效（Active）时间 | ＿＿ |
| 验证五项结果 | ①＿＿ ②＿＿ ③＿＿ ④＿＿ ⑤＿＿ |
| 24h 后看门狗 P95 / warn | ＿＿ |
| 结论（通过/回滚） | ＿＿ |

---

## 九、关联文档

- 诊断摘要与决策快照：[docs/17-工作台部署环境清单.md](17-工作台部署环境清单.md) §七
- 看门狗与聚合器（验证数据源）：[docs/21-智能化运维脚本闭环说明.md](21-智能化运维脚本闭环说明.md)
- 发布灰度与回滚总 SOP：docs/17 §五

---
**维护**：接入完成后本文状态改为 `status: stable` 并回填 §八；回滚则记录原因与 EdgeOne 评估结论。
