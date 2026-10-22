# VIBE: 面向应用开发的视觉与交互执行基准

[English](README.md) | [中文]

## 🌟 概览 (Overview)

**VIBE (Visual & Interactive Benchmark for Execution)** 确立了评估大语言模型（LLM）全栈软件工程能力的新标准。超越了近期依赖**静态截图**或**固定工作流快照**的现有基准，VIBE 首创 **Agent-as-a-Verifier (AaaV)** 范式，旨在精准评估模型“从零到一”构建生产级应用的真实能力。

通过将智能体部署在动态的容器化沙盒中，VIBE 从与其名称一一对应的三个关键维度进行分层评估：

1.  **Execution (执行 - 基础层):** 验证生成的项目能否成功编译、构建并启动，确保无致命运行错误。
2.  **Interactive (交互 - 核心层):** 确保在智能体动态操作过程中，所有用户需求得到满足且业务逻辑稳健。
3.  **Visual (视觉 - 美学层):** 量化用户界面的视觉效果、布局连贯性等美学质量。

## 🚀 核心特性 (Key Features)

* **Agent-as-a-Verifier (AaaV):** 一种新颖的评估框架，由具备视觉能力的智能体充当自主 QA 测试员。它们在 UI 中导航、点击按钮，并依据人类设计标准来评判应用的“观感”与体验。
* **真正的全栈覆盖:** 除了标准的 Web/Backend 任务，VIBE 覆盖了业界常被忽视的领域，包括 **原生 Android & iOS** 开发以及高保真的 **科学仿真**（物理/化学/计算机原理）。
* **多维评分体系:** 我们基于一套完善的奖励系统对应用进行评估：
    * **执行 (Execution):** 能否成功构建并在无崩溃的情况下运行？
    * **交互 (Interaction):** 逻辑在用户输入下是否鲁棒？
    * **美学 (Aesthetics):** UI 布局是否专业且视觉连贯？

## 📦 数据集包含内容

本仓库包含了 VIBE 基准测试的基础数据：
* **200 个精选任务:** 高质量的提示词 (Prompt) 规范，涵盖从简单工具到复杂全栈应用的各类场景。
* **结构化元数据:** 详细的难度标签与领域分类。
* **评估标准:** (即将推出) 我们的智能体验证者所使用的评分量表。

## 📅 路线图 (Roadmap)

- [x] **第一阶段:** 基准查询提示词 & 任务规范 (已发布: 2025年12月23日)
- [ ] **第二阶段:** 容器化沙盒环境 & Docker 镜像 (预计: 2026年1月)
- [ ] **第三阶段:** 开源 Agent 验证脚本 & 评分流水线 (预计: 2026年1月)

## 🧩 子集介绍 (Subsets)

| 子集 | 描述 |
|--------|-------------|
| **Web** | 对美学标准和复杂 DOM 交互有较高要求的现代前端应用 |
| **Simulation** | 需要高保真渲染的科学原理仿真（物理、化学、计算机科学） |
| **Android** | 原生 Android 应用开发 (Kotlin/Java) |
| **iOS** | 原生 iOS 应用开发 (Swift/Objective-C) |
| **Backend** | 侧重于 API 完整性与架构设计的服务端系统 |

## 📊 数据集统计 (Dataset Statistics)

| 子集 | 简单 (Easy) | 中等 (Medium) | 困难 (Hard) | 总计 |
|--------|:----:|:------:|:----:|:-----:|
| Web | 13 | 14 | 13 | 40 |
| Simulation | 13 | 14 | 13 | 40 |
| Android | 13 | 14 | 13 | 40 |
| iOS | 13 | 14 | 13 | 40 |
| Backend | 13 | 14 | 13 | 40 |
| **总计** | **65** | **70** | **65** | **200** |

## 📝 数据格式 (Data Format)

每个任务均为一个 JSON 对象，包含以下字段：

```json
{
  "idx": 1,
  "query": "Design and build a portfolio site for a top-tier design agency...",
  "domain": "web",
  "difficulty": "easy"
}

```

| 字段 | 描述 |
| --- | --- |
| `idx` | 唯一的任务标识符 |
| `query` | 自然语言形式的需求规范 |
| `domain` | 领域分类: `web`, `simulation`, `android`, `ios`, `backend` |
| `difficulty` | 难度等级: `easy` (简单), `medium` (中等), `hard` (困难) |

## 💻 数据集使用方法 (Dataset Usage)

```python
from datasets import load_dataset

# 加载完整数据集
dataset = load_dataset("MiniMaxAI/VIBE")

# 加载特定领域数据集 (例如: web)
web_tasks = dataset.filter(lambda x: x["domain"] == "web")

# 加载特定难度数据集 (例如: easy)
easy_tasks = dataset.filter(lambda x: x["difficulty"] == "easy")

```

## ⚖️ 评估方法 (Evaluation Methodology)

VIBE 的得分通过一套统一的流水线计算得出：

* **基础设施:** 标准化需求规范、容器化部署、动态交互环境
* **UI 类子集 (Web/Mobile/Sim):** 视觉智能体审计交互逻辑与视觉美学
* **后端 (Backend):** 自动化测试脚本的构建与执行
* **稳定性:** 结果取多次独立运行的平均值

## 引用 (Citation)

```bibtex
@misc{vibe2025,
  title={VIBE: Visual & Interactive Benchmark for Execution in Application Development},
  author={MiniMax},
  year={2025},
  publisher={Hugging Face}
}

```
