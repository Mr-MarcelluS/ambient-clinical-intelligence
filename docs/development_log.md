# Development log

## 2026-11-24 — Setup
- Inspected Linux, Python 3.12.14, approximately 10 GiB RAM, 7.5 GiB free disk; no NVIDIA GPU detected.
- GitHub account verified as Mr-MarcelluS. Repository creation failed with HTTP 403 (integration permission). User notified; local work continues.
- Selected CPU faster-whisper, deterministic evidence-preserving SOAP baseline, optional local Ollama adapter, FastAPI, Streamlit and SQLite.
- Investigated MedDialog, MIMIC-IV-Note, Omi SOAP and PriMock57. Prefer mock consultations with explicit reuse rights.

## Implementation and verification
- User created repository; it was public. Integration could not change visibility (403); user explicitly instructed to keep it public. Setup and core feature branches pushed.
- Implemented bounded audio decode, real CPU Whisper, exact spans, clinical grouping, conservative SOAP, validation, versioned SQLite persistence, FastAPI, Streamlit and approval-gated JSON/PDF/DOCX export.
- Created 100 fictional records, split by 20 scenario families. PriMock57 subset acquired and parsed (11 files; 3 consultations; 380 turns).
- Initial 36 unit/integration tests passed. Added structured grouping and UI tests; fixed AppTest path resolution. Final local suite: 38 tests passed, Ruff passed.
- Actual UI browser workflow verified and screenshots inspected. Fixed Streamlit's magic rendering of a conditional expression on the dashboard.
- First model download failed because the default HF cache was read-only. Retried with a workspace-local cache; tiny.en and base.en downloaded successfully.
- apt could not locate eSpeak packages; fetched Debian binary packages and extracted locally without system installation. Generated three fictional WAVs locally.
- Measured tiny.en and base.en transcription, retained reference and ASR outputs separately. Neither reliably transcribes clinical terms; errors documented.
- Actual FastAPI multipart WAV upload, ASR, extraction, transcript correction, versioned SOAP, simulated approval and all three exports passed. Review is automated QA, not a clinician's approval.
- Held-out postposed-negation failure retained without tuning. Evaluation is author-labeled synthetic testing, not independent clinical validation.
