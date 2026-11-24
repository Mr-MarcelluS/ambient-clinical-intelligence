# Ambient Clinical Intelligence — academic prototype report

**Date:** 24 November 2026. **Repository:** https://github.com/Mr-MarcelluS/ambient-clinical-intelligence

## Objective and implementation

Build and execute a practical documentation assistant for fictional consultations, preserving what was said and requiring human review. Implemented a six-view Streamlit application, FastAPI endpoints, transactional SQLite persistence, local faster-whisper audio recognition, dictionary/scoped-rule clinical extraction, exact character-span evidence, clinical grouping, extractive SOAP, optional constrained local LLM adapter, independent source validation, revision-aware approval, and JSON/PDF/DOCX export.

The CPU workflow was executed end to end, including actual WAV transcription and browser interaction. The original ASR transcript remains separate from corrected revisions. Human approval in QA was simulated and explicitly recorded as such.

## Data and experiment

Generated 100 fictional consultations from 20 scenario families, partitioned 60/20/20 by family. Gold entities, polarity, subjects, spans and SOAP are authored independently of the extraction code. Acquired three CC BY 4.0 PriMock57 mock consultations (11 text/license files, 380 parsed turns). Restricted or unclear-license sources were researched but not acquired. No actual patient data was used.

Held-out results: symptom mention F1 **1.000** (35 gold mentions), medication mention F1 **1.000** (5), duration F1 **1.000** (20), negation F1 **0.857** (20 negatives, 15 recognized), uncertainty F1 **1.000** (5), subject F1 **1.000** (45), exact entity span F1 **1.000** (45). Exact SOAP section accuracy **0.875**; source entity surface coverage **1.000**. Zero unsupported generated lines under the exact-source check. These small, template-based numbers do not establish clinical performance.

Actual speech evaluation used three locally synthesized recordings: tiny.en mean WER **0.1630**, base.en **0.1407**. Both made clinically material recognition errors. Eight authored unsupported-note mutations were detected (8/8), including dose, duration, polarity, subject and speaker changes. This is conservative quotation validation, not general semantic hallucination detection.

## Verification

38 local pytest tests passed; Ruff passed. Browser verification exercised consultation creation, evidence inspection, SOAP display, explicit approval and PDF download. Actual multipart audio API integration exercised transcription, correction, regeneration, approval and all export types. Linux and Windows GitHub Actions passed in run 45367950770. Screenshots are in `docs/screenshots/`.

## Limitations and unfinished validation

- No independent human/clinician verification of the labeled test set; this requested validation step remains outstanding.
- No clinician usability study or measured documentation time savings.
- Limited English terms and scope rules; postposed negation fails in the held-out set. Numeric template variants inflate record count without adding equivalent linguistic diversity.
- Source grounding cannot detect ASR errors or verify clinical truth. Exact quotes can preserve statements that the structured extractor labels incorrectly.
- No automatic speaker diarization; users must label audio transcripts. Timestamped ASR segments are available separately; manually corrected text has no reliable word-level time alignment.
- SOAP is extractive, not a fluent abstractive clinical summary. Conservative validation rejects otherwise valid paraphrases.
- Optional Ollama integration has failure/schema tests, but no actual LLM inference evaluation. No fine-tuning was performed.
- Microphone recording control exists but physical microphone capture was not tested in this environment.
- Local prototype only: no authentication, encryption, access-control policy, production retention or clinical certification.

## Future work

Obtain independent clinician annotation on a new, family-disjoint corpus; expand negation, temporal reasoning, family-history attribution and ontology coverage; measure clinically weighted ASR errors across accents/noise and test diarization; evaluate structured generation against clinician-verified gold; add secure deployment controls only after the research evaluation establishes acceptable behavior.

See `architecture.md` for flow and database diagrams, `dataset_report.md` for rights and acquisition, `model_selection.md` for model tradeoffs, and `evaluation_report.md` plus machine-readable result JSON for measurements.
