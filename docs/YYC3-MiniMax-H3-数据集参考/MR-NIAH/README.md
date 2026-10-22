---
license: mit
---

# Multi-Round Needles-In-A-Haystack (MR-NIAH) Evaluation

## Overview

Multi-Round Needles-In-A-Haystack (MR-NIAH) is an evaluation framework designed to assess long-context retrieval performance in large language models (LLMs). It serves as a crucial benchmark for retrieval tasks in long multi-turn dialogue contexts, revealing fundamental capabilities necessary for building lifelong companion AI assistants.

MR-NIAH extends the vanilla k-M NIAH (Kamradt, 2023) by creating a more challenging variation specifically tailored to evaluate a model's ability to recall information from earlier parts of a conversation across multiple dialogue rounds.

## Motivation

As LLMs are increasingly deployed in applications requiring long-term memory and contextual understanding across extended conversations, the ability to accurately retrieve specific information from earlier dialogue becomes critical. MR-NIAH addresses this need by providing a rigorous evaluation framework that:

1. Tests a model's ability to recall specific information from earlier in a conversation
2. Evaluates performance across varying context lengths (from 2K to 1M tokens)
3. Assesses recall accuracy at different positions within the conversation (25%, 50%, and 75%)
4. Provides a standardized benchmark for comparing different models and retrieval strategies

## Methodology

### Dataset Construction

MR-NIAH constructs "haystacks" as history dialogues, where:

1. User queries are synthetic but explicit requests for event descriptions and creative writing
2. Each query and its corresponding response are injected at specific positions (25%, 50%, and 75%) of the conversation
3. In the final round, the user requests the model to repeat a specific response from one of the earlier requests
4. The haystacks span from 2K to 1M tokens (up to approximately 2000 interactions)

### Evaluation Metrics

The evaluation focuses on the model's ability to accurately recall the requested information. Each ground truth response contains three core components, and the evaluation measures an adjusted recall score based on the model's ability to reproduce these components.

The scoring is implemented in `score.py`, which:
1. Processes model responses
2. Compares them against ground truth responses
3. Calculates an adjusted recall score based on the presence of key components

## Dataset Structure

The dataset is organized by language and token length:

```
data/
├── english/
│   ├── 2048_tokens.jsonl
│   ├── 10240_tokens.jsonl
│   ├── ...
│   └── 1024000_tokens.jsonl
└── chinese/
    ├── 2048_tokens.jsonl
    ├── 10240_tokens.jsonl
    ├── ...
    └── 1024000_tokens.jsonl
```

Each JSONL file contains evaluation examples with the following structure:

```json
{
  "messages": [
    {"role": "user", "content": "..."},
    {"role": "assistant", "content": "..."},
    ...
    {"role": "user", "content": "Please repeat the [specific content] you mentioned earlier"}
  ],
  "label": "The expected response that should be recalled",
  "length_class": 2048
}
```

## Usage

### Running Evaluations

Please refer to our GitHub page https://github.com/MiniMax-AI/MiniMax-01/tree/main/evaluation/MR-NIAH. 

### Interpreting Results

The evaluation produces scores that indicate:
- Overall recall performance across different context lengths
- Performance at different injection points (25%, 50%, 75%)
- Comparative performance against other models

## License

This evaluation framework is released under the same license as the MiniMax-01 repository.
