"""Transactional SQLite persistence; immutable transcript/note revisions."""
import json
import os
import sqlite3
import uuid
from contextlib import contextmanager
from pathlib import Path
from backend.schemas import Analysis, Note
from backend.pipeline import analyze
from ai.validation import validate
from ai.source_spans import attach_segment_times

SCHEMA = '''
CREATE TABLE IF NOT EXISTS consultations (
 id TEXT PRIMARY KEY, title TEXT NOT NULL, created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
 synthetic INTEGER NOT NULL CHECK(synthetic=1));
CREATE TABLE IF NOT EXISTS transcripts (
 id INTEGER PRIMARY KEY, consultation_id TEXT NOT NULL REFERENCES consultations(id) ON DELETE CASCADE,
 version INTEGER NOT NULL, original TEXT NOT NULL, corrected TEXT NOT NULL,
 UNIQUE(consultation_id, version));
CREATE TABLE IF NOT EXISTS audio_files (
 id INTEGER PRIMARY KEY, consultation_id TEXT NOT NULL REFERENCES consultations(id) ON DELETE CASCADE,
 path TEXT NOT NULL, metadata TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS transcript_segments (
 id INTEGER PRIMARY KEY, transcript_id INTEGER NOT NULL REFERENCES transcripts(id) ON DELETE CASCADE,
 start REAL NOT NULL, end REAL NOT NULL, text TEXT NOT NULL, confidence REAL);
CREATE TABLE IF NOT EXISTS clinical_findings (
 id INTEGER PRIMARY KEY, transcript_id INTEGER NOT NULL REFERENCES transcripts(id) ON DELETE CASCADE,
 entity TEXT NOT NULL, payload TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS source_spans (
 id INTEGER PRIMARY KEY, finding_id INTEGER NOT NULL REFERENCES clinical_findings(id) ON DELETE CASCADE,
 start INTEGER NOT NULL CHECK(start>=0), end INTEGER NOT NULL CHECK(end>start), text TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS soap_notes (
 id INTEGER PRIMARY KEY, consultation_id TEXT NOT NULL REFERENCES consultations(id) ON DELETE CASCADE,
 transcript_id INTEGER NOT NULL REFERENCES transcripts(id), version INTEGER NOT NULL,
 analysis TEXT NOT NULL, note TEXT NOT NULL, approved INTEGER NOT NULL DEFAULT 0,
 edit_count INTEGER NOT NULL DEFAULT 0, UNIQUE(consultation_id, version));
CREATE TABLE IF NOT EXISTS validation_warnings (
 id INTEGER PRIMARY KEY, note_id INTEGER NOT NULL REFERENCES soap_notes(id) ON DELETE CASCADE,
 code TEXT NOT NULL, payload TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS review_records (
 id INTEGER PRIMARY KEY, note_id INTEGER NOT NULL REFERENCES soap_notes(id) ON DELETE CASCADE,
 reviewer TEXT NOT NULL, review_seconds REAL NOT NULL CHECK(review_seconds>=0),
 warning_count INTEGER NOT NULL, created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP);
CREATE TABLE IF NOT EXISTS dataset_records (
 id TEXT PRIMARY KEY, dataset TEXT NOT NULL, split TEXT NOT NULL, payload TEXT NOT NULL);
CREATE INDEX IF NOT EXISTS idx_notes_consultation ON soap_notes(consultation_id,version);
CREATE INDEX IF NOT EXISTS idx_transcripts_consultation ON transcripts(consultation_id);
'''


class Conflict(ValueError):
    pass


class Store:
    def __init__(self, path=None):
        self.path = str(path or os.getenv('ACI_DB', 'runtime/aci.db'))
        Path(self.path).parent.mkdir(parents=True, exist_ok=True)
        with self.connect() as db:
            db.executescript(SCHEMA)

    @contextmanager
    def connect(self):
        db = sqlite3.connect(self.path, timeout=10)
        db.row_factory = sqlite3.Row
        db.execute('PRAGMA foreign_keys=ON')
        try:
            yield db
            db.commit()
        except Exception:
            db.rollback()
            raise
        finally:
            db.close()

    def _insert_note(self, db, cid, tid, version, analysis, note, edits):
        warnings = validate(analysis.transcript, analysis.findings, analysis.utterances, note)
        warnings += [w for w in analysis.warnings if w.code == 'provider_failure']
        analysis = analysis.model_copy(update={'note': note, 'warnings': warnings})
        nid = db.execute('INSERT INTO soap_notes(consultation_id,transcript_id,version,analysis,note,edit_count) VALUES(?,?,?,?,?,?)',
                         (cid, tid, version, analysis.model_dump_json(), note.model_dump_json(), edits)).lastrowid
        db.executemany('INSERT INTO validation_warnings(note_id,code,payload) VALUES(?,?,?)',
                       [(nid, w.code, w.model_dump_json()) for w in warnings])

    def _insert_transcript(self, db, cid, version, original, analysis):
        tid = db.execute('INSERT INTO transcripts(consultation_id,version,original,corrected) VALUES(?,?,?,?)',
                         (cid, version, original, analysis.transcript)).lastrowid
        for f in analysis.findings:
            fid = db.execute('INSERT INTO clinical_findings(transcript_id,entity,payload) VALUES(?,?,?)',
                             (tid, f.entity, f.model_dump_json())).lastrowid
            for span in [f.evidence, f.mention]:
                db.execute('INSERT INTO source_spans(finding_id,start,end,text) VALUES(?,?,?,?)',
                           (fid, span.start, span.end, span.text))
        return tid

    def create(self, transcript, title='Fictional consultation', audio=None):
        result = analyze(transcript)
        if audio:
            result = attach_segment_times(result, audio['segments'])
        cid = str(uuid.uuid4())
        with self.connect() as db:
            db.execute('INSERT INTO consultations(id,title,synthetic) VALUES(?,?,1)', (cid, title))
            tid = self._insert_transcript(db, cid, 1, transcript, result)
            self._insert_note(db, cid, tid, 1, result, result.note, 0)
            if audio:
                db.execute('INSERT INTO audio_files(consultation_id,path,metadata) VALUES(?,?,?)',
                           (cid, audio['path'], json.dumps(audio)))
                db.executemany('INSERT INTO transcript_segments(transcript_id,start,end,text,confidence) VALUES(?,?,?,?,?)',
                               [(tid, s['start'], s['end'], s['text'], s['avg_logprob']) for s in audio['segments']])
        return self.get(cid)

    def _current(self, db, cid):
        row = db.execute('SELECT * FROM soap_notes WHERE consultation_id=? ORDER BY version DESC LIMIT 1', (cid,)).fetchone()
        if row is None:
            raise KeyError('Consultation not found')
        return row

    def get(self, cid):
        with self.connect() as db:
            row = self._current(db, cid)
            transcript = db.execute('SELECT * FROM transcripts WHERE id=?', (row['transcript_id'],)).fetchone()
            c = db.execute('SELECT * FROM consultations WHERE id=?', (cid,)).fetchone()
            audio = db.execute('SELECT metadata FROM audio_files WHERE consultation_id=?', (cid,)).fetchone()
            return dict(c) | {'version': row['version'], 'approved': bool(row['approved']),
                'edit_count': row['edit_count'], 'original_transcript': transcript['original'],
                'analysis': json.loads(row['analysis']), 'audio': json.loads(audio[0]) if audio else None}

    def list(self):
        with self.connect() as db:
            return [dict(r) for r in db.execute('''SELECT c.*, n.version,n.approved,n.edit_count FROM consultations c
                JOIN soap_notes n ON n.consultation_id=c.id WHERE n.version=(SELECT MAX(version)
                FROM soap_notes WHERE consultation_id=c.id) ORDER BY c.created_at DESC''')]

    def revise(self, cid, expected_version, note: Note | None = None, transcript: str | None = None):
        result = analyze(transcript) if transcript is not None else None
        with self.connect() as db:
            db.execute('BEGIN IMMEDIATE')
            row = self._current(db, cid)
            if row['version'] != expected_version:
                raise Conflict('Stale version; reload before saving.')
            tid = row['transcript_id']
            if result:
                original = db.execute('SELECT original FROM transcripts WHERE id=?', (tid,)).fetchone()[0]
                tid = self._insert_transcript(db, cid, expected_version+1, original, result)
            else:
                result = Analysis.model_validate_json(row['analysis'])
            self._insert_note(db, cid, tid, expected_version+1, result, note or result.note, row['edit_count']+1)
        return self.get(cid)

    def approve(self, cid, expected_version, reviewer, acknowledge_warnings, review_seconds):
        if not reviewer.strip() or review_seconds < 0:
            raise ValueError('Reviewer and nonnegative review duration required.')
        with self.connect() as db:
            db.execute('BEGIN IMMEDIATE')
            row = self._current(db, cid)
            if row['version'] != expected_version:
                raise Conflict('Stale version; reload before approval.')
            result = Analysis.model_validate_json(row['analysis'])
            if any(w.severity == 'error' for w in result.warnings):
                raise ValueError('Resolve unsupported claims or invalid evidence before approval.')
            if result.warnings and not acknowledge_warnings:
                raise ValueError('Acknowledge validation warnings before approval.')
            db.execute('UPDATE soap_notes SET approved=1 WHERE id=?', (row['id'],))
            db.execute('INSERT INTO review_records(note_id,reviewer,review_seconds,warning_count) VALUES(?,?,?,?)',
                       (row['id'], reviewer.strip(), review_seconds, len(result.warnings)))
        return self.get(cid)

    def delete(self, cid):
        with self.connect() as db:
            # Notes reference transcripts, so remove notes before cascading the consultation.
            db.execute('DELETE FROM soap_notes WHERE consultation_id=?', (cid,))
            changed = db.execute('DELETE FROM consultations WHERE id=?', (cid,)).rowcount
            if not changed:
                raise KeyError('Consultation not found')
