import os
import time
from backend.schemas import Analysis, Warning
from ai.extraction import extract
from ai.soap import baseline, OllamaProvider
from ai.validation import validate


def analyze(transcript: str) -> Analysis:
    started = time.perf_counter()
    findings, units = extract(transcript)
    note = baseline(units)
    provider = 'extractive'
    failures = []
    if os.getenv('ACI_LLM_PROVIDER', 'extractive') == 'ollama':
        try:
            note = OllamaProvider().generate(units)
            provider = 'ollama-evidence-selection'
        except Exception as exc:
            failures.append(Warning(code='provider_failure', reason=f'Local LLM failed ({type(exc).__name__}); extractive fallback used.'))
    return Analysis(transcript=transcript, findings=findings, utterances=units, note=note,
                    warnings=validate(transcript, findings, units, note)+failures,
                    processing_seconds=time.perf_counter()-started, provider=provider)
