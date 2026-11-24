import logging
import sqlite3
import uuid
from pathlib import Path
from typing import Literal
from fastapi import FastAPI, File, Form, UploadFile, HTTPException
from fastapi.responses import Response, JSONResponse
from dotenv import load_dotenv
from backend.database import Store, Conflict
from backend.schemas import ConsultationInput, NoteUpdate, Approval
from backend.exports import export
from ai.speech import transcribe, MAX_BYTES

load_dotenv()
app = FastAPI(title='ACI — Synthetic Clinical Documentation', version='0.1.0')
logger = logging.getLogger(__name__)


@app.exception_handler(ValueError)
async def invalid(request, exc):
    return JSONResponse(status_code=409 if isinstance(exc, Conflict) else 422, content={'detail': str(exc)})


@app.exception_handler(KeyError)
async def missing(request, exc):
    return JSONResponse(status_code=404, content={'detail': 'Consultation not found'})


@app.exception_handler(sqlite3.Error)
async def database_error(request, exc):
    logger.error('Database operation failed: %s', type(exc).__name__)
    return JSONResponse(status_code=503, content={'detail': 'Database unavailable; retry later.'})


@app.get('/health')
def health():
    return {'status': 'ok', 'mode': 'synthetic-only'}


@app.post('/consultations', status_code=201)
def create(data: ConsultationInput):
    return Store().create(data.transcript, data.title)


@app.get('/consultations')
def history():
    return Store().list()


@app.get('/consultations/{cid}')
def read(cid: str):
    return Store().get(cid)


@app.put('/consultations/{cid}/note')
def update_note(cid: str, data: NoteUpdate):
    return Store().revise(cid, data.expected_version, note=data.note)


class TranscriptUpdate(ConsultationInput):
    expected_version: int


@app.put('/consultations/{cid}/transcript')
def update_transcript(cid: str, data: TranscriptUpdate):
    return Store().revise(cid, data.expected_version, transcript=data.transcript)


@app.post('/consultations/{cid}/approve')
def approve(cid: str, data: Approval):
    return Store().approve(cid, **data.model_dump())


@app.get('/consultations/{cid}/export/{kind}')
def download(cid: str, kind: Literal['json', 'pdf', 'docx']):
    payload, mime = export(Store().get(cid), kind)
    return Response(payload, media_type=mime, headers={'Content-Disposition': f'attachment; filename="aci-note.{kind}"'})


@app.delete('/consultations/{cid}', status_code=204)
def delete(cid: str):
    Store().delete(cid)
    return Response(status_code=204)


@app.post('/audio', status_code=201)
async def upload(file: UploadFile = File(...), synthetic_confirmed: bool = Form(...)):
    if not synthetic_confirmed:
        raise HTTPException(422, 'Only fictional recordings are permitted.')
    suffix = Path(file.filename or '').suffix.lower()
    if suffix not in {'.wav', '.mp3', '.m4a', '.ogg', '.flac'}:
        raise HTTPException(422, 'Unsupported audio type.')
    target = Path('runtime/audio') / f'{uuid.uuid4()}{suffix}'
    target.parent.mkdir(parents=True, exist_ok=True)
    try:
        size = 0
        with target.open('wb') as out:
            while chunk := await file.read(1024*1024):
                size += len(chunk)
                if size > MAX_BYTES:
                    raise ValueError('Audio exceeds 25 MB.')
                out.write(chunk)
        # Run CPU work outside the async event loop.
        from starlette.concurrency import run_in_threadpool
        audio = await run_in_threadpool(transcribe, target)
        return await run_in_threadpool(Store().create, audio['transcript'], 'Fictional audio consultation', audio)
    except (ValueError, sqlite3.Error):
        target.unlink(missing_ok=True)
        raise
    except Exception as exc:
        target.unlink(missing_ok=True)
        logger.error('ASR failed: %s', type(exc).__name__)
        raise HTTPException(503, 'Speech model unavailable. Check model download and settings; text input remains available.') from exc
    finally:
        await file.close()
