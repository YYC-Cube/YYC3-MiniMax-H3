---
license: cc-by-sa-4.0
task_categories:
- text-to-speech
---

## Overview
To assess the multilingual zero-shot voice cloning capabilities of TTS models, we have constructed a test set encompassing 24 languages. This dataset provides both audio samples for voice cloning and corresponding test texts.
Specifically, the test set for each language includes:
100 distinct test sentences.

Audio samples from two speakers (one male and one female) carefully selected from the Mozilla Common Voice (MCV) dataset, intended for voice cloning.

Researchers can clone the target voices using the provided audio samples and then synthesize the test texts. The resulting synthetic audio can then be evaluated for metrics such as Word Error Rate (WER) and speaker similarity(SIM), eg. [seed-tts-eval](https://github.com/BytedanceSpeech/seed-tts-eval).

## 24 Languages
Chinese, English, Cantonese, Japanese, Korean, Arabic, Spanish, Turkish, Indonesian, Portuguese, French, Italian, Dutch, Vietnamese, German, Russian, Ukrainian, Thai, Polish, Romanian, Greek, Czech, Finnish, Hindi.

## Data Format
The dataset is organized as follows:
```
├── speaker/...
│       Contains two audio files for each language (corresponding to male and female speakers).
│       Transcriptions for these audio files are also provided in prompt_text.txt.
└── text/...
        Contains a test text file for each language.
        Each line in the file follows the format: cloning_audio_filename|text_to_be_synthesized
        Example (Korean): korean_female|내 나이 아홉살 처음 알게 된 사실이 잇었다. 생일 초를 끄기 전에는 소원을 빌어야 한다는 것.
        (Here, korean_female refers to the corresponding Korean female speaker audio filename in the speaker/ directory, used for voice cloning.)
```

## Future Plans
We plan to expand this dataset in the future by adding more languages. Our goal is to establish it as a standard benchmark for evaluating and comparing multilingual TTS models.

Paper: https://huggingface.co/papers/2505.07916
Project page: https://minimax-ai.github.io/tts_tech_report

## Citation

```
@misc{minimax2025minimaxspeechintrinsiczeroshottexttospeech,
      title={MiniMax-Speech: Intrinsic Zero-Shot Text-to-Speech with a Learnable Speaker Encoder}, 
      author={Bowen Zhang, Congchao Guo, Geng Yang, Hang Yu, Haozhe Zhang, Heidi Lei, Jialong Mai, Junjie Yan, Kaiyue Yang, Mingqi Yang, Peikai Huang, Ruiyang Jin, Sitan Jiang, Weihua Cheng, Yawei Li, Yichen Xiao, Yiying Zhou, Yongmao Zhang, Yuan Lu, Yucen He},
      year={2025},
      eprint={2505.07916},
      archivePrefix={arXiv},
      primaryClass={eess.AS},
      url={https://arxiv.org/abs/2505.07916}, 
}
```