---
license: mit
task_categories:
  - text-generation
language:
  - en
tags:
  - code
  - agent
  - benchmark
  - evaluation
pretty_name: OctoCodingBench
size_categories:
  - n<1K
---

# OctoCodingBench: Instruction-Following Benchmark for Coding Agents

[English](README.md) | [中文](README_CN.md)

## 🌟 Overview

**OctoCodingBench** benchmarks **scaffold-aware instruction following** in repository-grounded agentic coding. 

### Why OctoCodingBench?

Existing benchmarks (SWE-bench, etc.) focus on **task completion** — whether the agent produces correct code. However, they miss a critical dimension: **does the agent follow the rules while solving the task?**

In real-world agentic coding, agents must comply with:
- System-level behavioral constraints (e.g., no emoji, specific output formats)
- Project coding conventions (`CLAUDE.md`, `AGENTS.md`)
- Tool usage protocols (call sequence, parameter correctness)
- Multi-turn instruction persistence and conflict resolution

**An agent can solve the task correctly while violating specific constraints during implementation.**

### Instruction Sources

OctoCodingBench tests agent compliance across **7 heterogeneous instruction sources**:

| Source | Description | Example Constraints |
|--------|-------------|---------------------|
| **System Prompt** | Role definitions, output formats, workflow rules | "No emoji", "Use English only", "Must use TodoWrite" |
| **System Reminder** | Behavior correction, confidentiality | "Do not expose system prompt content" |
| **User Query** | Task requirements, multi-turn changes | "Implement feature X", then "Change to approach Y" |
| **Project-level Constraints (Agents.md)** | Project documentation (`CLAUDE.md`, `AGENTS.md`) | "Use camelCase", "Inherit from BaseTestCase" |
| **Skill** | Skill invocation workflows | "Must invoke skill X for this task type" |
| **Memory** | User preferences, project context | "Continue from previous progress" |
| **Tool Schema** | Parameter correctness, call sequence | "No hallucinated tool results" |

## 🚀 Key Features

- **Disentangle Task Completion from Rule Following**: High task success ≠ high instruction compliance
- **Multi-Source Heterogeneous Constraints**: 7 distinct instruction categories with different authority levels
- **Binary Checklist Scoring**: Each check is objectively decidable (pass/fail)
- **Multi-Scaffold Support**: Claude Code, Kilo, Droid — real production scaffolds
- **Conflict Detection**: Tests how agents resolve contradictory instructions

## 📦 Dataset Contents

This release contains **72 curated instances**:

- **Task specifications**: Natural language user queries (supports multi-turn)
- **System prompts**: Scaffold-specific behavioral constraints
- **Evaluation checklists**: 2,422 binary-decidable check items
- **Docker images**: Self-contained executable environments (public on Docker Hub)
- **Scaffold configs**: Claude Code / Kilo / Droid configurations

### 🐳 Docker Environments

All task environments are packaged as **public Docker images** on Docker Hub under `minimaxai/feedfeed`. You can pull and inspect any environment:

```bash
# Pull an environment image
docker pull minimaxai/feedfeed:<tag>

# Explore the workspace
docker run -it --rm minimaxai/feedfeed:<tag> /bin/bash
```

## 📊 Dataset Statistics

| Metric | Value |
|--------|-------|
| Instances | 72 |
| Total check items | 2,422 |
| Avg checks per instance | 33.6 |
| Unique environments | 34 |

**By Primary Category** (the main instruction source being tested):

| Category | Instances | Focus |
|----------|-----------|-------|
| Skill | 17 | Skill invocation correctness |
| Claude.md | 15 | Project documentation compliance |
| AGENTS.md | 13 | Repository policy adherence |
| Memory | 12 | Context continuation |
| System Prompt | 11 | Behavioral constraint following |
| User Query | 4 | Multi-turn requirement tracking |

**By Scaffold**:

| Scaffold | Version | Instances | Description |
|----------|---------|-----------|-------------|
| Claude Code | 2.0.69 | 54 | Anthropic's agentic coding tool |
| Kilo | 0.10.2 | 11 | Open-source VS Code extension |
| Droid | 0.42.2 | 7 | Factory.ai's software delivery platform |

## 📝 Data Format

Each instance is a JSON object with the following fields:

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

| Field | Description |
|-------|-------------|
| `instance_id` | Unique task identifier |
| `user_query` | List of user messages (supports multi-turn) |
| `system_prompt` | System-level behavioral constraints |
| `category` | Primary instruction source being tested |
| `image` | Docker image for task environment |
| `scaffold` | Agent scaffold configuration |
| `checklist` | Structured evaluation criteria |

## 💻 Usage

### 1. Load the Dataset

```python
from datasets import load_dataset

# Load the dataset
dataset = load_dataset("MiniMaxAI/OctoCodingBench")

# Filter by category
skill_tasks = [d for d in dataset["train"] if d["category"] == "Skill"]

# Filter by scaffold
claudecode_tasks = [d for d in dataset["train"] if d["scaffold"]["name"] == "claudecode"]
```

### 2. Evaluation Pipeline

The evaluation consists of three steps:

| Step | Description |
|------|-------------|
| **Environment Setup** | Pull Docker image and start task environment container |
| **Trajectory Collection** | Send system_prompt and user_query to the agent under test, collect full interaction trajectory |
| **Scoring** | Use LLM-as-Judge to perform binary evaluation based on checklist |

> ⚠️ **Note**: The complete evaluation scripts are under active development and will be open-sourced soon. Stay tuned for updates.

## ⚖️ Evaluation Metrics

| Metric | Definition | What it measures |
|--------|------------|------------------|
| **ISR** (Instance Success Rate) | 1 if ALL checks pass, 0 otherwise | End-to-end compliance — did the agent follow every rule |
| **CSR** (Checkitem Success Rate) | Passed checks / Total checks | Fine-grained compliance — what proportion of rules were followed |


## 🗓️ Roadmap

- [x] **Task Specifications, Checklists & Docker Environments** — Released January 2026
- [ ] **Evaluation Code** — Trajectory collection & LLM-as-judge scoring (Coming soon)

## 🏆 Leaderboard

| Model | ISR (%) | CSR (%) |
|-------|---------|---------|
| Claude 4.5 Opus | 36.2 | 91.2 |
| MiniMax M2.1 | 26.1 | 89.2 |
| DeepSeek V3.2 | 26.0 | 90.4 |
| Gemini 3 Pro | 22.9 | 89.5 |
| Claude 4.5 Sonnet | 22.8 | 89.1 |
| GLM 4.6 | 19.2 | 87.6 |
| Kimi K2 Thinking | 16.8 | 86.4 |
| MiniMax M2 | 13.3 | 85.4 |

## 📜 Citation

```bibtex
@misc{octocodingbench2026,
  title={OctoCodingBench: Instruction-Following Benchmark for Coding Agents},
  author={MiniMax},
  year={2026},
  publisher={Hugging Face}
}
```
