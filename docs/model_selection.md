# Model and dependency selection

## Speech

Primary engine: [faster-whisper](https://github.com/SYSTRAN/faster-whisper) 1.2.1 with CTranslate2 int8 CPU inference. PyAV decodes WAV/MP3/etc without requiring a separate ffmpeg installation. Default model: [Systran/faster-whisper-tiny.en](https://huggingface.co/Systran/faster-whisper-tiny.en), approximately 75 MB weights, MIT model card. `base.en` (approximately 145 MB) was also downloaded and measured. Both run comfortably in this approximately 10 GiB CPU environment. GPU optional via `ACI_ASR_DEVICE=cuda` and suitable compute type/CUDA libraries.

| Model | Three-sample mean WER | Per-sample ASR seconds |
|---|---:|---|
| tiny.en, int8 CPU | 0.1630 | 1.171, 0.599, 0.481 |
| base.en, int8 CPU | 0.1407 | 2.163, 1.416, 0.950 |

Audio is only 5–8 seconds per sample, synthesized locally by eSpeak NG. First measured sample includes model initialization. Normalization lowercases, removes punctuation and collapses whitespace; numbers are not normalized, so `three` versus `3` counts as an error. This is not a representative ASR benchmark. Both models made clinically material errors. Base performed better on the third recording but still misrecognized medication wording; tiny remains the fast demonstration default. Select `base.en` or a local model path with `ACI_ASR_MODEL`. Original references, hypotheses and per-sample metrics are retained in `data/evaluation` and `data/synthetic/audio`.

## Clinical NLP

Investigated [spaCy](https://spacy.io/usage/models) and [scispaCy](https://allenai.github.io/scispacy/). General spaCy NER is not a clinical conversation labeling model; scispaCy's biomedical models focus on scientific text and do not solve conversational negation, temporal correction or speaker attribution alone. This baseline therefore uses explicit terminology dictionaries and NegEx-style scoped rules, without a heavyweight model or unsupported claims of clinical NER accuracy. It is replaceable via `ai/extraction.py`.

## SOAP / local LLM

Default generation is deterministic, extractive, and needs no key or paid provider. Optional Ollama adapter uses [Qwen2.5 3B](https://ollama.com/library/qwen2.5:3b) as a configurable candidate for JSON evidence selection. It is not downloaded or benchmarked in this task. Its model license must be reviewed for the intended use; the 3B variant has its own Qwen license, not an assumed blanket Apache grant. No inference claim is made for it. Only malformed-response/network-failure behavior and evidence-selection validation were tested with mocks.

The provider contract returns existing evidence IDs grouped by their supplied section. It does not ask the model to independently diagnose, prescribe or paraphrase. Missing/extra IDs and wrong sections are rejected and fall back to the baseline. A free-form LLM note generator would need a substantially stronger clinical validation study; this prototype intentionally uses a constrained generation contract.

Dependencies are bounded in `requirements.txt`; `requirements-lock.txt` records exact versions installed and tested on Python 3.12. Linux and Windows CI is configured. No model training or fine-tuning was performed.
