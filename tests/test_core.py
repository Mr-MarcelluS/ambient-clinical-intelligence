import sqlite3
from unittest.mock import patch
import pytest
from fastapi.testclient import TestClient
from backend.pipeline import analyze
from ai.extraction import polarity_for
from ai.validation import validate
from ai.soap import OllamaProvider
from ai.speech import load_audio
from backend.database import Store, Conflict
from backend.exports import export
from backend.api import app


@pytest.mark.parametrize('text,entity,polarity', [
    ('I have headache.','headache','positive'),
    ('I deny fever.','fever','negative'),
    ('I might have fever.','fever','uncertain'),
    ('No nausea or vomiting.','vomiting','negative'),
    ("I haven't experienced fever or vomiting.",'fever','negative'),
    ('I have cough, but no fever.','cough','positive'),
    ('I have no fever and I have cough.','cough','positive'),
])
def test_polarity(text,entity,polarity):
    a=analyze('Patient: '+text)
    assert polarity_for(a.findings,entity)==[polarity]


def test_not_mentioned():
    assert polarity_for(analyze('Patient: I have headache.').findings,'fever')==['not mentioned']


def test_multiple_duration_spans():
    a=analyze('Patient: I have headache for three days, but no fever or vomiting.')
    assert len(a.findings)==3
    assert a.findings[0].duration=='three days'
    for f in a.findings:
        assert a.transcript[f.mention.start:f.mention.end]==f.mention.text


def test_subject_and_speaker():
    a=analyze('Patient: My father has diabetes.\nDoctor: Do you have fever?')
    assert len(a.findings)==1
    assert a.findings[0].subject=='father'
    assert a.findings[0].evidence.speaker=='Patient'


def test_medication():
    a=analyze('Patient: I take metformin 500 mg twice daily and aspirin 75 mg daily.')
    assert [(f.dosage,f.frequency) for f in a.findings]==[('500 mg','twice daily'),('75 mg','daily')]


def test_decimal_vitals():
    a=analyze('Doctor: Temperature measured at 36.8 degrees.')
    assert a.note.O=='[Doctor] Temperature measured at 36.8 degrees.'


@pytest.mark.parametrize('text,code',[
    ('Patient: I have fever. I do not have fever.','contradiction'),
    ('Patient: I had fever yesterday, but no fever today.','temporal_change'),
    ('Patient: Pain started yesterday. Sorry, I mean two days ago.','correction'),
    ('I have headache.','unknown_speaker'),
])
def test_warnings(text,code):
    assert code in [w.code for w in analyze(text).warnings]


def test_missing_objective():
    a=analyze('Patient: I have a headache.')
    assert a.note.O=='Objective findings not documented.'


@pytest.mark.parametrize('section,claim',[
    ('A','[Doctor] Diagnosis: pneumonia.'),('P','[Doctor] Take aspirin 500 mg.'),
    ('O','[Doctor] Lungs are clear.'),('S','[Patient] I have no headache for three days.'),
    ('S','[Patient] I have headache for five days.'),('S','[Doctor] I have headache for three days.'),
])
def test_unsupported_and_changed_facts(section,claim):
    a=analyze('Patient: I have headache for three days.')
    note=a.note.model_copy(update={section:claim})
    assert any(w.code=='unsupported_claim' for w in validate(a.transcript,a.findings,a.utterances,note))


def test_source_mismatch():
    a=analyze('Patient: I have headache.')
    a.findings[0].mention.start=0
    assert any(w.code=='source_mismatch' for w in validate(a.transcript,a.findings,a.utterances,a.note))


def test_empty():
    with pytest.raises(ValueError):
        analyze('  ')


def test_invalid_audio(tmp_path):
    p=tmp_path/'fake.wav'
    p.write_bytes(b'not audio')
    with pytest.raises(ValueError):
        load_audio(p)


def test_silent_audio(tmp_path):
    import wave
    p=tmp_path/'silent.wav'
    with wave.open(str(p),'wb') as f:
        f.setnchannels(1)
        f.setsampwidth(2)
        f.setframerate(16000)
        f.writeframes(b'\0'*32000)
    with pytest.raises(ValueError,match='silence'):
        load_audio(p)


def test_malformed_llm():
    with patch('ai.soap.httpx.post') as post:
        post.return_value.json.return_value={'response':'not json'}
        with pytest.raises(ValueError):
            OllamaProvider().generate(analyze('Patient: Headache.').utterances)


def test_failed_provider_fallback(monkeypatch):
    monkeypatch.setenv('ACI_LLM_PROVIDER','ollama')
    with patch('ai.soap.httpx.post',side_effect=RuntimeError('offline')):
        a=analyze('Patient: Headache.')
    assert a.provider=='extractive'
    assert any(w.code=='provider_failure' for w in a.warnings)


def test_llm_invented_ids():
    with patch('ai.soap.httpx.post') as post:
        post.return_value.json.return_value={'response':'{"S":["fake"],"O":[],"A":[],"P":[]}'}
        with pytest.raises(ValueError):
            OllamaProvider().generate(analyze('Patient: Headache.').utterances)


@pytest.fixture
def store(tmp_path):
    return Store(tmp_path/'test.db')


def test_review_version_and_exports(store):
    r=store.create('Patient: I have headache.')
    assert not r['approved']
    with pytest.raises(ValueError):
        export(r,'json')
    with pytest.raises(ValueError):
        store.approve(r['id'],1,'Demo',False,2)
    r=store.approve(r['id'],1,'Demo',True,2)
    for fmt,header in [('pdf',b'%PDF'),('docx',b'PK'),('json',b'{')]:
        assert export(r,fmt)[0].startswith(header)
    r=store.revise(r['id'],1,transcript='Patient: No headache.')
    assert not r['approved'] and r['version']==2
    assert r['original_transcript']=='Patient: I have headache.'
    with pytest.raises(Conflict):
        store.approve(r['id'],1,'Demo',True,2)
    with pytest.raises(Conflict):
        store.revise(r['id'],1,transcript='Patient: Cough.')


def test_unsupported_blocks_approval(store):
    r=store.create('Patient: Headache.')
    note=analyze('Patient: Headache.').note.model_copy(update={'A':'Pneumonia.'})
    store.revise(r['id'],1,note=note)
    with pytest.raises(ValueError,match='unsupported'):
        store.approve(r['id'],2,'Demo',True,3)


def test_database_error(tmp_path):
    p=tmp_path/'bad.db'
    p.write_bytes(b'garbage database')
    with pytest.raises(sqlite3.DatabaseError):
        Store(p)


def test_delete(store):
    r=store.create('Patient: Headache.')
    store.delete(r['id'])
    assert store.list()==[]
    with pytest.raises(KeyError):
        store.get(r['id'])


def test_api_e2e(tmp_path,monkeypatch):
    monkeypatch.setenv('ACI_DB',str(tmp_path/'api.db'))
    c=TestClient(app)
    assert c.get('/health').status_code==200
    assert c.post('/consultations',json={'transcript':'Patient: Cough.','synthetic_confirmed':False}).status_code==422
    response=c.post('/consultations',json={'transcript':'Patient: Cough.','synthetic_confirmed':True})
    assert response.status_code==201
    cid=response.json()['id']
    assert c.get(f'/consultations/{cid}/export/json').status_code==422
    assert c.post(f'/consultations/{cid}/approve',json={'expected_version':1,'reviewer':'Demo','acknowledge_warnings':True,'review_seconds':3}).status_code==200
    assert c.get(f'/consultations/{cid}/export/pdf').content.startswith(b'%PDF')
    assert c.get('/consultations/missing').status_code==404
    assert c.post('/audio',data={'synthetic_confirmed':'true'},files={'file':('bad.wav',b'bad','audio/wav')}).status_code==422
    assert c.delete(f'/consultations/{cid}').status_code==204


def test_api_database_failure(monkeypatch):
    with patch('backend.api.Store',side_effect=sqlite3.OperationalError('bad')):
        assert TestClient(app).get('/consultations').status_code==503


def test_structured_allergy_history_and_vitals():
    a=analyze('Patient: I am allergic to amoxicillin. My mother has asthma.\nDoctor: Temperature is 37 degrees.\nDoctor: Follow-up in a week.')
    assert a.structured['allergies'][0]['text']=='I am allergic to amoxicillin.'
    assert a.structured['medical_history'][0]['speaker']=='Patient'
    assert a.structured['vital_signs'][0]['speaker']=='Doctor'
    assert a.structured['follow_up']


def test_audio_source_times_and_edited_alignment(store):
    text='I have headache. No fever.'
    audio={'path':'fictional.wav','segments':[
        {'start':1.2,'end':2.5,'text':'I have headache.','avg_logprob':-0.2},
        {'start':3.0,'end':4.0,'text':'No fever.','avg_logprob':-0.2}]}
    r=store.create(text,audio=audio)
    assert [f['mention']['timestamp'] for f in r['analysis']['findings']]==[1.2,3.0]
    r=store.revise(r['id'],1,transcript='Patient: I have headache. No fever.')
    assert all(f['mention']['timestamp'] is None for f in r['analysis']['findings'])
