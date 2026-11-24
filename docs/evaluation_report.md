# Evaluation report

Author-labeled synthetic family-disjoint evaluation; no clinician verification. Surface coverage is not semantic accuracy.

| Split | Cases | Symptom F1 | Negation F1 | Uncertainty F1 | Section exact | Mean seconds |
|---|---:|---:|---:|---:|---:|---:|
| development | 60 | 1.000 | 1.000 | 1.000 | 0.938 | 0.000089 |
| validation | 20 | 1.000 | 1.000 | 0.000 | 0.750 | 0.000168 |
| test | 20 | 1.000 | 0.857 | 1.000 | 0.875 | 0.000176 |

Full precision, recall, F1 and denominators for medications, duration, subjects and exact spans are in `data/evaluation/metrics.json`.

The 100 cases are 20 scenario families with five numeric variants each; effective linguistic diversity is 20, not 100. Families are disjoint across splits. No training or fine-tuning was performed. Gold labels are independently specified in the data generator, not produced by the extractor. They have not been manually verified by an independent human or clinician.

Held-out failures are retained and reported, not used to tune the rules. Postposed negation ("Fever is absent") is a known extraction failure. Exact quotations preserve it in the note, but the structured polarity label can be wrong.

SOAP is extractive: exact section matching and surface coverage do not establish clinical adequacy or semantic validation. Unsupported line checking deliberately rejects valid paraphrases. No human review time savings are claimed. Review durations recorded in smoke tests are not an efficiency study.

## Speech and validation measurements

Three locally synthesized samples: mean WER 0.1630 for tiny.en and 0.1407 for base.en, CPU int8. The references and actual hypotheses are retained; medication and symptom errors remain visible. See `data/evaluation/audio_metrics_tiny.json` and `audio_metrics.json`. A fourth, full consultation recording is a demonstration, excluded from this three-sample comparison.

Eight authored unsupported-note mutations were detected (8/8); the unmodified baseline had zero error-level warnings. See `data/evaluation/validation_metrics.json`. Exact-line matching detects any modified statement, so this result does not imply semantic precision on valid paraphrases.

Evidence coverage and unsupported extraction span rate measure literal span validity, not clinical validity. Gold-line completeness and negative-turn verbatim preservation are conservative text-based proxies; they are not clinician judgments. Input contradictions are counted separately from generated unsupported lines; a semantic generated-note contradiction rate has not been independently measured.
