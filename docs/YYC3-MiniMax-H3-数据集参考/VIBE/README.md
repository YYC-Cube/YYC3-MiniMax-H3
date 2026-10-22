---
license: mit
task_categories:
- text-generation
language:
- en
tags:
- benchmark
- web-development
- app-development
- agent-as-a-verifier
- full-stack
- vibe-coding
size_categories:
- n<1K
---

# VIBE: Visual & Interactive Benchmark for Execution in Application Development

[English] | [中文](README_CN.md)

## 🌟 Overview

**VIBE (Visual & Interactive Benchmark for Execution)** sets a new standard for evaluating Large Language Models (LLMs) in full-stack software engineering. Moving beyond recent benchmarks that rely on **static screenshots** or **rigid workflow snapshots** to assess application development, VIBE pioneers the **Agent-as-a-Verifier (AaaV)** paradigm to assess the true "0-to-1" capability of constructing production-ready applications.

By deploying intelligent agents into dynamic, containerized sandboxes, VIBE performs a hierarchical evaluation across three critical dimensions that directly mirror its name:

1.  **Execution (The Foundation):** Verifying that the generated project compiles, builds, and launches successfully without fatal errors.
2.  **Interactive (The Core):** Ensuring all user requirements are met and the business logic remains robust during active agent operation.
3.  **Visual (The Apex):** Quantify the aesthetic qualities of the user interface, such as visual effects and layout consistency.

## 🚀 Key Features

* **Agent-as-a-Verifier (AaaV):** A novel evaluation framework where vision-capable agents act as autonomous QA testers. They navigate the UI, click buttons, and judge the "look and feel" against human design standards.
* **True Full-Stack Coverage:** Beyond standard Web/Backend tasks, VIBE targets often-neglected domains including **Native Android & iOS** development and high-fidelity **Scientific Simulations** (Physics/Chemistry/CS).
* **Multi-Dimensional Scoring:** We evaluate applications based on a comprehensive reward system:
    * **Execution:** Does it build and run without crashing?
    * **Interaction:** Is the logic robust under user inputs?
    * **Aesthetics:** Is the UI layout professional and visually coherent?

## 📦 What's Included in This Dataset

This repository contains the foundational data for the VIBE benchmark:
* **200 Curated Tasks:** High-quality prompt specifications ranging from simple tools to complex full-stack applications.
* **Structured Metadata:** Detailed difficulty labeling and domain categorization.
* **Evaluation Criteria:** (Coming soon) The rubric used by our agent verifiers.

## 📅 Roadmap

- [x] **Phase 1:** Benchmark query prompts & task specifications (Released: December 23, 2025)
- [ ] **Phase 2:** Containerized sandbox environments & Docker images (Expected: January 2026)
- [ ] **Phase 3:** Open-source Agent-Verifier scripts & Scoring pipeline (Expected: January 2026)

## 🧩 Subsets

| Subset | Description |
|--------|-------------|
| **Web** | Frontend apps with high aesthetic standards and complex DOM interactions |
| **Simulation** | Scientific simulations (Physics, Chemistry, CS) requiring high-fidelity rendering |
| **Android** | Native Android development (Kotlin/Java) |
| **iOS** | Native iOS development (Swift/Objective-C) |
| **Backend** | Server-side systems focusing on API integrity and architecture |

## 📊 Dataset Statistics

| Subset | Easy | Medium | Hard | Total |
|--------|:----:|:------:|:----:|:-----:|
| Web | 13 | 14 | 13 | 40 |
| Simulation | 13 | 14 | 13 | 40 |
| Android | 13 | 14 | 13 | 40 |
| iOS | 13 | 14 | 13 | 40 |
| Backend | 13 | 14 | 13 | 40 |
| **Total** | **65** | **70** | **65** | **200** |

## 📝 Data Format

Each task is a JSON object with the following fields:

```json
{
  "idx": 1,
  "query": "Design and build a portfolio site for a top-tier design agency...",
  "domain": "web",
  "difficulty": "easy"
}
```

| Field | Description |
| --- | --- |
| `idx` | Unique task identifier |
| `query` | Natural language requirement specification |
| `domain` | One of: `web`, `simulation`, `android`, `ios`, `backend` |
| `difficulty` | One of: `easy`, `medium`, `hard` |

## 💻 Dataset Usage

```python
from datasets import load_dataset

# Load the full dataset
dataset = load_dataset("MiniMaxAI/VIBE")

# Load special domain dataset. eg: web
web_tasks = dataset.filter(lambda x: x["domain"] == "web")

# Load special difficulty dataset; eg: easy
easy_tasks = dataset.filter(lambda x: x["difficulty"] == "easy")

```

## ⚖️ Evaluation Methodology

Scores are computed through a unified pipeline:

* **Infrastructure:** Standardized specs, containerized deployment, dynamic interaction environments
* **UI Subsets (Web/Mobile/Sim):** Vision-capable agents audit interaction logic and visual aesthetics
* **Backend:** Automated test-script construction and execution
* **Stability:** Results averaged over multiple independent runs

## Citation

```bibtex
@misc{vibe2025,
  title={VIBE: Visual & Interactive Benchmark for Execution in Application Development},
  author={MiniMax},
  year={2025},
  publisher={Hugging Face}
}

```
