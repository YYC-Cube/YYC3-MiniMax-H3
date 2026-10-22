---
license: mit
task_categories:
  - text-generation
language:
  - zh
tags:
  - code
  - agent
  - benchmark
  - evaluation
pretty_name: OctoCodingBench
size_categories:
  - n<1K
---

# OctoCodingBench: 编程智能体指令遵循基准

[English](README.md) | [中文](README_CN.md)

## 🌟 概览

**OctoCodingBench** 评估代码仓库场景下的**脚手架感知指令遵循能力**。

### 为什么需要 OctoCodingBench？

现有基准测试（如 SWE-bench）主要关注**任务完成度**——智能体是否生成了正确的代码。然而，它们忽略了一个关键维度：**智能体在完成任务的过程中是否遵循了规则？**

在真实的智能体编程场景中，Agent 必须遵守：
- 系统级行为约束（如禁止使用 emoji、特定输出格式）
- 项目编码规范（`CLAUDE.md`、`AGENTS.md`）
- 工具使用协议（调用顺序、参数正确性）
- 多轮指令持续性和冲突解决

**智能体可能正确完成任务，却可能在实现的过程中违反具体的约束。** 

### 指令来源

OctoCodingBench 测试智能体对 **7 种异构指令来源**的遵循程度：

| 来源 | 描述 | 示例约束 |
|------|------|----------|
| **System Prompt** | 角色定义、输出格式、工作流规则 | "禁止使用 emoji"、"必须使用英文"、"必须使用 TodoWrite" |
| **System Reminder** | 行为纠正、信息保密 | "不要暴露系统提示内容" |
| **User Query** | 任务需求、多轮变更 | "实现功能 X"，然后 "改用方案 Y" |
| **项目级约束(Agents.md)** | 项目文档（`CLAUDE.md`、`AGENTS.md`） | "使用 camelCase"、"继承 BaseTestCase" |
| **技能 (Skill)** | 技能调用流程 | "此类任务必须调用技能 X" |
| **记忆 (Memory)** | 用户偏好、项目上下文 | "从上次进度继续" |
| **Tool Schema** | 参数正确性、调用顺序 | "禁止幻觉工具结果" |

## 🚀 核心特性

- **区分任务完成与规则遵循**：高任务成功率 ≠ 高指令遵循率
- **多源异构约束**：7 种不同权限级别的指令类别
- **二元检查清单评分**：每项检查可客观判定（通过/失败）
- **多脚手架支持**：Claude Code、Kilo、Droid — 真实生产环境脚手架
- **冲突检测**：测试智能体如何解决矛盾指令

## 📦 数据集内容

本次发布包含 **72 个精选实例**：

- **任务规范**：自然语言用户查询（支持多轮）
- **系统提示**：脚手架特定的行为约束
- **评估检查清单**：2,422 个二元判定检查项
- **Docker 镜像**：自包含可执行环境（Docker Hub 公开）
- **脚手架配置**：Claude Code / Kilo / Droid 配置

### 🐳 Docker 环境

所有任务环境都打包为 **公开的 Docker 镜像**，托管在 Docker Hub 的 `minimaxai/feedfeed` 命名空间下。你可以直接拉取并查看任意环境：

```bash
# 拉取环境镜像
docker pull minimaxai/feedfeed:<tag>

# 进入容器查看
docker run -it --rm minimaxai/feedfeed:<tag> /bin/bash
```

## 📊 数据集统计

| 指标 | 数值 |
|------|------|
| 实例数 | 72 |
| 总检查项数 | 2,422 |
| 平均每实例检查项 | 33.6 |
| 独立环境数 | 34 |

**按主要类别**（被测试的主要指令来源）：

| 类别 | 实例数 | 关注点 |
|------|--------|--------|
| Skill | 17 | 技能调用正确性 |
| Claude.md | 15 | 项目文档遵循 |
| AGENTS.md | 13 | 仓库策略遵守 |
| Memory | 12 | 上下文延续 |
| System Prompt | 11 | 行为约束遵循 |
| User Query | 4 | 多轮需求跟踪 |

**按脚手架**：

| 脚手架 | 版本 | 实例数 | 描述 |
|--------|------|--------|------|
| Claude Code | 2.0.69 | 54 | Anthropic 的智能体编程工具 |
| Kilo | 0.10.2 | 11 | 开源 VS Code 扩展 |
| Droid | 0.42.2 | 7 | Factory.ai 的软件交付平台 |

## 📝 数据格式

每个实例是一个 JSON 对象，包含以下字段：

```json
{
  "instance_id": "md-course-builder-conventional-commits",
  "user_query": ["Implement the feature as specified..."],
  "system_prompt": "You are a CLI assistant...",
  "category": "Claude.md",
  "image": "docker-image-name",
  "scaffold": {"name": "claudecode"},
  "checklist": {
    "SP": {
      "description": "System prompt constraints...",
      "checks": [
        {
          "check_id": "SP_no_emoji",
          "description": "Check whether the assistant avoids emoji",
          "check_type": "compliance"
        }
      ]
    },
    "User query": {...}
  }
}
```

| 字段 | 描述 |
|------|------|
| `instance_id` | 唯一任务标识符 |
| `user_query` | 用户消息列表（支持多轮） |
| `system_prompt` | 系统级行为约束 |
| `category` | 被测试的主要指令来源 |
| `image` | 任务环境 Docker 镜像 |
| `scaffold` | 智能体脚手架配置 |
| `checklist` | 结构化评估标准 |

## 💻 使用方法

### 1. 加载数据集

```python
from datasets import load_dataset

# 加载数据集
dataset = load_dataset("MiniMaxAI/OctoCodingBench")

# 按类别筛选
skill_tasks = [d for d in dataset["train"] if d["category"] == "Skill"]

# 按脚手架筛选
claudecode_tasks = [d for d in dataset["train"] if d["scaffold"]["name"] == "claudecode"]
```

### 2. 评测流程

评测分为三个步骤：

| 步骤 | 说明 |
|------|------|
| **环境准备** | 拉取 Docker 镜像，启动任务环境容器 |
| **轨迹收集** | 将 system_prompt 和 user_query 发送给待测智能体，收集完整交互轨迹 |
| **评分判定** | 基于 checklist 使用 LLM-as-Judge 对轨迹进行二元判定 |

> ⚠️ **注意**：完整的评测脚本正在完善中，即将开源。敬请关注本仓库更新。

## ⚖️ 评估指标

| 指标 | 定义 | 衡量内容 |
|------|------|----------|
| **ISR**（实例成功率） | 所有检查项通过为 1，否则为 0 | 端到端合规性——智能体是否遵循了每条规则 |
| **CSR**（检查项成功率） | 通过检查项 / 总检查项 | 细粒度合规性——遵循了多大比例的规则 |


## 🗓️ 路线图

- [x] **任务规范、检查清单与 Docker 环境** — 2026年1月已发布
- [ ] **评测代码** — 轨迹收集与 LLM-as-judge 评分（即将开源）

## 🏆 排行榜

| 模型 | ISR (%) | CSR (%) |
|------|---------|---------|
| Claude 4.5 Opus | 36.2 | 91.2 |
| MiniMax M2.1 | 26.1 | 89.2 |
| DeepSeek V3.2 | 26.0 | 90.4 |
| Gemini 3 Pro | 22.9 | 89.5 |
| Claude 4.5 Sonnet | 22.8 | 89.1 |
| GLM 4.6 | 19.2 | 87.6 |
| Kimi K2 Thinking | 16.8 | 86.4 |
| MiniMax M2 | 13.3 | 85.4 |

## 📜 引用

```bibtex
@misc{octocodingbench2026,
  title={OctoCodingBench: Instruction-Following Benchmark for Coding Agents},
  author={MiniMax},
  year={2026},
  publisher={Hugging Face}
}
```

