---
language:
- en
- zh
license: mit
task_categories:
- text-generation
tags:
- logical reasoning
configs:
- config_name: easy
  data_files:
  - split: train
    path: synlogic_easy/train.parquet
  - split: validation
    path: synlogic_easy/validation.parquet
- config_name: hard
  data_files:
  - split: train
    path: synlogic_hard/train.parquet
  - split: validation
    path: synlogic_hard/validation.parquet
---

# SynLogic Dataset

SynLogic is a comprehensive synthetic logical reasoning dataset designed to enhance logical reasoning capabilities in Large Language Models (LLMs) through reinforcement learning with verifiable rewards. 

* 🐙 **GitHub Repo:** [https://github.com/MiniMax-AI/SynLogic](https://github.com/MiniMax-AI/SynLogic)
* 📜 **Paper (arXiv):** [https://arxiv.org/abs/2505.19641](https://arxiv.org/abs/2505.19641)

## Dataset Description

SynLogic contains 35 diverse logical reasoning tasks with automatic verification capabilities, making it ideal for reinforcement learning training.

### Key Features

- **35 Task Types**: Including Sudoku, Game of 24, Cipher, Arrow Maze, Cryptarithm, and more
- **Verifiable Rewards**: All samples have automatic verifiers for correctness checking
- **Controllable Difficulty**: Adjustable difficulty parameters for each task
- **Two Versions**: Easy (7B models) and Hard (32B models)

## Dataset Configurations

### SynLogic-Easy
- **Target**: 7B parameter models
- **Tasks**: 27 tasks
- **Samples**: ~16,000 training instances

### SynLogic-Hard  
- **Target**: 32B parameter models
- **Tasks**: All 35 tasks
- **Samples**: ~33,000 training instances


## Usage

```python
from datasets import load_dataset

# Load easy version for 7B models
dataset_easy = load_dataset("MiniMaxAI/SynLogic", "easy")

# Load hard version for 32B models  
dataset_hard = load_dataset("MiniMaxAI/SynLogic", "hard")
```

## News

**[2025-07-02]** Fixed extra info information for boolean_expressions


**[2025-06-12]** Fixed duplicate prompts in ARC AGI tasks. Updated both training and validation datasets to remove redundant prompt content. See commit [3416fc5](https://huggingface.co/datasets/MiniMaxAI/SynLogic/commit/3416fc57cf3ee47cac749eaf2c0d430617a99041) for details.

## Performance

Models trained on SynLogic achieve state-of-the-art logical reasoning performance:
- **BBEH**: 25.5% (+6 points vs DeepSeek-R1-Distill-Qwen-32B)
- **KOR-Bench**: 62.2%
- Strong transfer to mathematical reasoning tasks


## Citation
Please cite our paper if you find our work helpful:

```bibtex
@misc{liu2025synlogic,
      title={SynLogic: Synthesizing Verifiable Reasoning Data at Scale for Learning Logical Reasoning and Beyond}, 
      author={Junteng Liu and Yuanxiang Fan and Zhuo Jiang and Han Ding and Yongyi Hu and Chi Zhang and Yiqi Shi and Shitong Weng and Aili Chen and Shiqi Chen and Yunan Huang and Mozhi Zhang and Pengyu Zhao and Junjie Yan and Junxian He},
      year={2025},
      eprint={2505.19641},
      archivePrefix={arXiv},
      primaryClass={cs.AI},
      url={https://arxiv.org/abs/2505.19641}, 
}
```