# Dataset acquisition and licensing report

Reviewed 24 November 2026. No real patient data is used in this prototype. External source files are excluded from Git.

| Source | Contents / size | Rights and access | Decision / acquisition |
|---|---|---|---|
| [PriMock57](https://github.com/babylonhealth/primock57) | 57 simulated primary-care consultations; audio, TextGrid transcripts, JSON clinical notes | [CC BY 4.0](https://github.com/babylonhealth/primock57/blob/main/LICENSE.md); attribution, retain license, identify adaptations; commercial reuse and redistribution allowed under those conditions | Downloaded and validated a 3-consultation text subset (11 files including README and license); normalized 380 turns. Exact bytes, hashes, revision and URLs in `data/manifests/primock57.json`. No external audio downloaded. |
| [MedDialog / UCSD26](https://huggingface.co/datasets/UCSD26/medical_dialog) | English and Chinese web medical dialogues; English roughly 260,000 conversations; text | Dataset card attributes underlying content rights to source consultation sites. Code license is not a grant over consultation content. Commercial use/redistribution not established here. | Research only, not downloaded. Do not scrape consultations; seek rights-holder permission and privacy review before any future use. |
| [MIMIC-IV-Note v2.2](https://physionet.org/content/mimic-iv-note/2.2/) | Large deidentified clinical-note corpus; millions of notes; no consultation audio | PhysioNet Credentialed Health Data License 1.5.0; credentialing, training and individual DUA. Redistribution restricted. Not an unrestricted commercial dataset. | Not downloaded. Create PhysioNet account, complete credentialing and approved human-subjects/data training, then sign the specific MIMIC-IV-Note DUA. Real patient-derived data is outside this prototype's scope. |
| [PhysioNet](https://physionet.org/about/faqs/) | Repository of clinical datasets with dataset-specific access rules | Hosting does not imply open licensing; restricted datasets require their own access checks | Investigated MIMIC-IV-Note; no bypass of access controls. |
| [Omi medical-dialogue-to-soap-summary](https://huggingface.co/datasets/omi-health/medical-dialogue-to-soap-summary) | 10,000 synthetic dialogue/SOAP pairs, JSON; 9,250/500/250 split | Card says downstream use requires permission from original NoteChat authors; underlying PMC case-report provenance also needs review. No unconditional redistribution/commercial grant established. | Not downloaded. Although useful for SOAP research, excluded until permissions and provenance are resolved. |
| ACI fictional corpus | 100 JSONL consultations, 20 families × 5 numeric variants; exact entity spans, labels, expected SOAP and warnings; three local TTS WAVs | Original project-authored text under MIT; fictional, no patient identities. Local eSpeak NG-generated audio; synthesis tool GPL-licensed, not bundled. | Generated and schema/span validated. Small authored text and result JSON committed; WAV files regenerated locally. |

## Attribution

PriMock57: Alex Papadopoulos Korfiatis, Francesco Moramarco, Radmila Sarac, and Aleksandar Savkov (2022), **PriMock57: A Dataset of Primary Care Mock Consultations**, Babylon Health. [ACL paper](https://aclanthology.org/2022.acl-short.65/). Source files downloaded unchanged; the preprocessing script merges speaker tiers in timestamp order, an adaptation. Retain CC BY 4.0 attribution when using its outputs.

## Reproduce acquisition

```sh
python -m scripts.download_datasets
python -m scripts.preprocess_dialogues
python -m scripts.generate_synthetic_data
python -m scripts.validate_dataset
```

The downloader pins the resolved source revision in the manifest, saves SHA-256 hashes and validates JSON/TextGrid parsing. It raises errors on failed HTTP responses; it does not claim success after a failed download. The source configuration is `data/manifests/sources.json`. The default download uses the current upstream revision; consult the recorded revision to reproduce the exact run.

## Coverage and limitations

PriMock57 supports dialogue understanding, timestamps and note-structure research; the acquired subset is used only for format inspection, not accuracy claims. Authored labels cover entities, polarity, uncertainty, duration, subject, source offsets, SOAP and validation challenges. Local TTS supports bounded speech evaluation. There is no externally validated clinical entity/negation benchmark in this delivery. Clinical diversity, accents, overlapping speakers and natural microphone noise remain untested. Synthetic records and labels have not received independent human clinical verification.
