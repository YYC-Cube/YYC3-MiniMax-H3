---
language:
- zh
- en
license: apache-2.0
task_categories:
- text-generation
size_categories:
- 1K<n<10K
configs:
- config_name: seeds_zh
  data_files:
  - split: test
    path: data/zh/seeds.parquet
- config_name: seeds_en
  data_files:
  - split: test
    path: data/en/seeds.parquet
- config_name: dialogues_zh
  data_files:
  - split: test
    path: data/zh/dialogues.parquet
- config_name: dialogues_en
  data_files:
  - split: test
    path: data/en/dialogues.parquet
- config_name: evaluations_zh
  data_files:
  - split: test
    path: data/zh/evaluations.parquet
- config_name: evaluations_en
  data_files:
  - split: test
    path: data/en/evaluations.parquet
---

# Role-play Benchmark

A comprehensive benchmark for evaluating Role-play Agents in **Chinese** and **English** scenarios.

## Dataset Summary

Role-play Benchmark is designed to evaluate Role-play Agents' ability to deliver immersive role-play experiences through **Situated Reenactment**. Unlike traditional benchmarks with verifiable answers, Role-play is fundamentally **non-verifiable**, e.g., there's no single "correct" response when a tsundere character is asked "Do you like me?". Instead, we focus on detecting **misalignment**: identifying what clearly does NOT fit the character setting.

The benchmark addresses three core challenges in Role-play Agents:

- **Worlds (Consistency & Logic)**: Evaluating the agent's ability to eliminate technical glitches and "catastrophic forgetting," ensuring long-term adherence to established relationships and world laws to prevent immersion-breaking contradictions.

- **Stories (Narrative Progression)**: Assessing whether the agent drives the plot forward with semantic variety and motivated character evolution, avoiding repetitive patterns, stagnation, or out-of-character (OOC) behaviors.

- **User Preferences (Interaction Quality)**: Testing the agent’s interactive boundaries and responsiveness—ensuring it avoids speaking for the user, responds to context, and consistently provides "hooks" to invite further engagement.

### Key Features

- **Situated Reenactment**: Evaluates agent performance at specific `{World} × {Stories}` coordinates for given `{User Preferences}`
- **Model-on-Model Self-Play**: Uses a carefully crafted User Simulator to generate multi-turn dialogue trajectories
- **Negative Evaluation (Flooring)**: Focuses on detecting misalignment rather than defining "perfect" responses
- **Multi-Dimensional Scoring**: Combines Basics, Logic, Knowledge, Diversity, Content Logic, and Interaction metrics

### Data Source

#### Data Source, Privacy & Scope
All dialogues in this release are synthetically constructed by our data team. This is a partial subset of the full benchmark, and the released samples are intentionally skewed toward a chat-oriented role-play style, designed to mirror online user interaction patterns in conversational settings.

#### Controlled Variations & Robustness Evaluation
To better assess robustness, the dataset intentionally includes controlled perturbations in input formats, writing styles, and prompt structures. We also introduce light variations to selected user-side fields (e.g., initial_user_input, user_setting) in parts of the data. A key evaluation objective is output stability—whether models can maintain consistent, high-quality role-play behavior under noisy or non-standard inputs.

#### Design
We explored multiple situated reenactment designs to reflect different ways role-play scenarios unfold in practice, and use two complementary datasets (en/zh) to showcase these design choices under controlled vs. diverse user-side conditions.

- English (en): We standardize user-side fields (e.g., user_name, user_setting, initial_user_input) to isolate NPC performance and make cross-NPC comparisons cleaner.
- Chinese (zh): We allow scenario-dependent variations in user_setting and initial_user_input to reflect diverse user personas and different conversation starting points, enabling evaluation of model behavior across a broader range of initial conditions.

## Dataset Structure

### Configurations

This dataset has **2 configurations**:

| Config | Language | Seeds | Dialogues | Description |
|--------|----------|-------|-----------|-------------|
| `zh` | Chinese | 50 | 1,650 | Chinese role-play scenarios |
| `en` | English | 45 | 1,485 | English role-play scenarios |

### Data Fields

#### Seeds Table (`seeds_zh` / `seeds_en`)

Role-play scenario seeds containing character settings and initial context.

| Field | Type | Description |
|-------|------|-------------|
| `id` | string | Unique scenario identifier (zh_dialogue_01, en_dialogue_01, etc.) |
| `ai_name` | string | AI character name |
| `ai_setting` | string | Detailed character description including personality, background, and behavioral traits |
| `user_name` | string | User character name |
| `user_setting` | string | User character setting/persona |
| `ai_prologue` | string | AI opening message that initiates the role-play scenario |
| `initial_user_input` | string | First user input to start the conversation |

#### Dialogues Table (`dialogues_zh` / `dialogues_en`)

Generated multi-turn dialogue trajectories from agent self-play.

| Field | Type | Description |
|-------|------|-------------|
| `seed_id` | string | Reference to the seed scenario (foreign key to Seeds.id) |
| `model_name` | string | Name of the agent being evaluated |
| `run_id` | string | Run identifier for multi-sampling (run_1, run_2, run_3) |
| `dialogue` | string | Full dialogue history as list of {round, role, text} objects |
| `num_turns` | int64 | Total number of dialogue turns in the session |

#### Evaluations Table (`evaluations_zh` / `evaluations_en`)

Session-level evaluation scores across 6 dimensions (0-100 scale).

| Field | Type | Description |
|-------|------|-------------|
| `seed_id` | string | Reference to the seed scenario (foreign key to Seeds.id) |
| `model_name` | string | Name of the agent being evaluated |
| `run_id` | string | Run identifier matching the dialogue |
| `basics_score` | float | Text quality score (garbled text, language mixing, repetition) |
| `logic_score` | float | Logical consistency score (character confusion, spatial errors) |
| `knowledge_score` | float | Factual reliability score (virtual/real world balance) |
| `diversity_score` | float | Expression variety and narrative momentum score |
| `content_logic_score` | float | Narrative coherence and OOC detection score |
| `interaction_score` | float | User interaction quality score (AI speaks for user, ignores user, over-refusal) |



## Evaluation Metrics

The evaluation directly maps to the three core objectives:

| Core Objective | Evaluation Question | Dimensions (Weight) |
|----------------|---------------------|---------------------|
| **Worlds**  | Can the agent accurately understand and maintain complex world settings? | Basics, Logic, Knowledge |
| **Stories**  | Can the agent push narratives forward with life and rhythm, avoiding mechanical repetition? | Diversity, Content Logic |
| **User Preferences**  | Can the agent sensitively perceive user intent and respond appropriately? | Interaction |

### Detailed Dimensions

**Worlds Dimensions:**
- **Basics**: Text quality — avoiding garbled text, language mixing, severe repetition
- **Logic**: Logical consistency — preventing character confusion, spatial errors, pronoun reference confusion
- **Knowledge**: Factual reliability — balancing rules between virtual and real worlds

**Stories Dimensions:**
- **Diversity**: Expression variety and narrative momentum — penalizing dialogue stagnation and mechanical loops
- **Content Logic**: Narrative coherence and OOC (Out-of-Character) detection — allowing character evolution with proper buildup

**User Preferences Dimensions:**
- **Interaction**: Penalizes behaviors like *AI Speaks for User* (acting on user's behalf), *AI Ignores User* (self-talking), and *Over Refusal* (excessive rejection of interaction).

### Evaluation Protocol

- **Long-Context Interaction**: Each session consists of **100 dialogue turns** to test stability and consistency over time.
- **Multi-Sampling**: We conduct **3 independent sessions** per scenario to account for generation variance.
- **Chunked Judging**: Conversations are sliced into **20-turn chunks** for stable LLM-as-Judge evaluation.
- **Human Calibration**: The automated metrics are regularly calibrated against human preference data to ensure alignment.

## Leaderboard

### Overall Rankings

| Rank | Model | Overall | 95% CI | Worlds (50%) | 95% CI | Stories (25%) | 95% CI | Preferences (25%) | 95% CI |
|------|-------|---------|--------|--------------|--------|---------------|--------|-------------------|--------|
| 1 | MiniMax-M2-her | **84.65** 👑 | [83.62, 85.68] | **80.55** 👑 | [79.20, 81.91] | 79.97 | [78.95, 81.00] | **97.51** 👑 | [97.12, 97.91] |
| 2 | doubao-1.5-pro | 80.64 | [79.58, 81.70] | 72.83 | [71.35, 74.30] | 81.73 | [80.93, 82.52] | 95.18 | [94.68, 95.69] |
| 3 | gpt-5.1 | 80.63 | [79.65, 81.61] | 76.62 | [75.33, 77.92] | 72.21 | [71.16, 73.27] | 97.05 | [96.79, 97.32] |
| 4 | claude-opus-4.5-highthinking | 76.62 | [75.50, 77.73] | 67.23 | [65.57, 68.89] | 82.10 | [81.41, 82.79] | 89.90 | [89.44, 90.36] |
| 5 | gemini-3-pro | 75.60 | [74.52, 76.68] | 62.72 | [61.17, 64.26] | **83.87** 👑 | [83.01, 84.72] | 93.08 | [92.71, 93.46] |
| 6 | claude-opus-4.5-lowthinking | 71.19 | [70.10, 72.28] | 60.68 | [59.14, 62.22] | 76.89 | [76.13, 77.65] | 86.51 | [86.00, 87.02] |
| 7 | claude-sonnet-4.5 | 69.35 | [68.22, 70.47] | 55.72 | [54.20, 57.25] | 75.66 | [74.70, 76.62] | 90.28 | [89.80, 90.76] |
| 8 | gemini-2.5-pro | 68.23 | [67.15, 69.31] | 52.36 | [50.88, 53.85] | 82.11 | [81.27, 82.95] | 86.08 | [85.56, 86.60] |
| 9 | deepseek-v3.1 | 64.22 | [62.95, 65.49] | 51.11 | [49.47, 52.74] | 66.45 | [65.26, 67.64] | 88.21 | [87.61, 88.82] |
| 10 | deepseek-v3.2 | 60.27 | [59.21, 61.34] | 45.81 | [44.44, 47.18] | 66.64 | [65.65, 67.62] | 82.83 | [82.29, 83.37] |
| 11 | grok-4.1 | 48.47 | [47.46, 49.49] | 29.87 | [28.65, 31.10] | 47.51 | [46.56, 48.45] | 86.64 | [85.96, 87.32] |


## 📖 Citation

```bibtex
@dataset{MiniMaxAI_role-play_bench_2026,
  title={Role-play Benchmark},
  author={MiniMax},
  year={2026},
  publisher={Hugging Face},
  url={https://huggingface.co/datasets/MiniMaxAI/role-play-bench}
}
```

## 📄 License

CC BY 4.0 / CC BY-SA 4.0
