# API

Launch `python -m uvicorn backend.api:app --host 127.0.0.1 --port 8001`. Interactive OpenAPI: http://127.0.0.1:8001/docs.

| Method / route | Purpose |
|---|---|
| GET `/health` | Status and synthetic-only mode |
| POST `/consultations` | JSON transcript, `synthetic_confirmed: true`, optional title |
| GET `/consultations` | Current session summaries |
| GET `/consultations/{id}` | Current analysis, original transcript, version and approval |
| PUT `/consultations/{id}/transcript` | Corrected transcript, synthetic confirmation, expected version; regenerate |
| PUT `/consultations/{id}/note` | `note: {S,O,A,P}`, expected version; validate new revision |
| POST `/consultations/{id}/approve` | Expected version, reviewer, acknowledgment, review seconds |
| GET `/consultations/{id}/export/{json,pdf,docx}` | Approved current version only |
| DELETE `/consultations/{id}` | Delete session database records |
| POST `/audio` | Multipart file plus synthetic_confirmed; local ASR and draft creation |

Example input:

```json
{"transcript":"Patient: I have headache, but no fever.","synthetic_confirmed":true,"title":"Fictional demo"}
```

404 means unknown session; 409 stale revision; 422 invalid input or unapproved/unsupported export; 503 database/model unavailable. Audio transcription runs outside the async event loop. No authentication: bind loopback and use only fictional data. No public service deployment is supplied.
