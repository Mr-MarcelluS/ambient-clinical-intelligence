import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import html
import time
import uuid
import streamlit as st
from dotenv import load_dotenv
from backend.database import Store
from backend.schemas import Note
from backend.exports import DISCLAIMER, export
from ai.speech import transcribe, MAX_BYTES

load_dotenv()
st.set_page_config(page_title='ACI | Ambient Clinical Intelligence', page_icon='◈', layout='wide')
st.markdown('''<style>
.stApp {background:#f5f8fb} h1,h2,h3 {color:#163c48} [data-testid="stSidebar"] {background:#e8f0f1}
[data-testid="stMetric"] {background:white;border:1px solid #d9e4e8;border-radius:12px;padding:18px}
.block-container {padding-top:2rem} .eyebrow {color:#287a80;font-size:12px;letter-spacing:2px;font-weight:700}
</style>''', unsafe_allow_html=True)
st.sidebar.markdown('## ◈ ACI\nAmbient Clinical Intelligence')
st.sidebar.caption('RESEARCH WORKSPACE · SYNTHETIC ONLY')
page = st.sidebar.radio('Workspace', ['Dashboard', 'New Consultation', 'Transcript and Extraction', 'SOAP Note', 'Validation and Review', 'History and Export'])
st.sidebar.divider()
st.sidebar.caption(DISCLAIMER)
store = Store()
rows = store.list()


def current():
    if not rows:
        st.info('Start a fictional consultation to open this workspace.')
        st.stop()
    ids = [r['id'] for r in rows]
    active = st.session_state.get('active', ids[0])
    cid = st.selectbox('Consultation', ids, index=ids.index(active) if active in ids else 0,
                       format_func=lambda cid: next(r['title']+' · '+cid[:8] for r in rows if r['id'] == cid))
    st.session_state.active = cid
    st.session_state.setdefault('review_start_'+cid, time.monotonic())
    return store.get(cid)


def warnings(record):
    for w in record['analysis']['warnings']:
        getattr(st, 'error' if w['severity']=='error' else 'info' if w['severity']=='info' else 'warning')(w['code']+' — '+w['reason'])
        if w['evidence']:
            with st.expander('Inspect supporting evidence', expanded=False):
                for e in w['evidence']:
                    st.caption(f"{e['speaker']} · characters {e['start']}–{e['end']}")
                    st.code(e['text'], language=None)


st.markdown('<div class="eyebrow">EVIDENCE FIRST · HUMAN REVIEWED</div>', unsafe_allow_html=True)
st.title(page if page != 'Dashboard' else 'Clinical documentation, with a source.')
if page == 'Dashboard':
    st.write('Turn fictional consultations into traceable SOAP drafts. Inspect the evidence, review every section, then approve.')
    a,b,c = st.columns(3)
    a.metric('Consultations', len(rows))
    b.metric('Notes generated', len(rows))
    c.metric('Pending review', sum(not r['approved'] for r in rows))
    st.subheader('Your review workspace')
    left,right = st.columns([2,1])
    with left:
        st.dataframe(rows, hide_index=True, use_container_width=True) if rows else st.info('No sessions yet. Open New Consultation to try the fictional demo.')
    with right:
        st.success('Local documentation pipeline ready')
        st.write('**01** Capture or paste\n\n**02** Inspect and correct\n\n**03** Review and export')
        st.caption('Speech model downloads on first use. No automatic speaker diarization. No cloud LLM calls.')
    st.info(DISCLAIMER)
elif page == 'New Consultation':
    st.caption('Only fictional or simulated consultations. Do not enter real patient information.')
    confirmed = st.checkbox('I confirm this consultation is fictional and contains no real patient information.')
    mode = st.radio('Input method', ['Text transcript', 'Audio upload', 'Microphone'], horizontal=True)
    title = st.text_input('Session title', 'Fictional consultation')
    demo = 'Patient: I have a headache for three days, but no fever or vomiting.\nDoctor: On examination, temperature is 37 degrees.\nDoctor: My assessment is a possible migraine.\nDoctor: Plan: rest and return in two days if symptoms persist.'
    if mode == 'Text transcript':
        text = st.text_area('Speaker-labeled transcript', demo, height=230)
        if st.button('Generate documentation', type='primary', disabled=not confirmed):
            try:
                with st.status('Extracting facts and validating SOAP…'):
                    record = store.create(text, title)
                st.session_state.active = record['id']
                st.success('Draft created. Open Transcript and Extraction to review the evidence.')
            except Exception as exc:
                st.error(str(exc))
    else:
        audio = st.file_uploader('Upload WAV, MP3, M4A, OGG or FLAC · max 25 MB / 10 minutes', type=['wav','mp3','m4a','ogg','flac']) if mode == 'Audio upload' else st.audio_input('Record a fictional consultation')
        if audio:
            st.audio(audio)
        if st.button('Transcribe and generate', type='primary', disabled=not (confirmed and audio)):
            path = None
            try:
                if audio.size > MAX_BYTES:
                    raise ValueError('Audio exceeds 25 MB.')
                path = Path('runtime/audio') / (str(uuid.uuid4())+Path(audio.name).suffix)
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_bytes(audio.getvalue())
                with st.status('Decoding audio → local Whisper → evidence extraction…'):
                    result = transcribe(path)
                    record = store.create(result['transcript'], title, audio=result)
                st.session_state.active = record['id']
                st.success(f"Transcribed in {result['processing_seconds']:.2f}s. Correct the transcript and add speaker labels next.")
                st.write(result['transcript'])
            except Exception as exc:
                if path:
                    path.unlink(missing_ok=True)
                st.error(f'Audio processing failed ({type(exc).__name__}): {exc}')
elif page == 'Transcript and Extraction':
    r = current()
    a = r['analysis']
    with st.expander('Original transcript and ASR timestamps'):
        st.code(r['original_transcript'], language=None)
        if r['audio']:
            st.dataframe(r['audio']['segments'], hide_index=True)
    text = st.text_area('Correct transcript · use Doctor: and Patient: labels', a['transcript'], height=240, key=f"transcript_{r['id']}_{r['version']}")
    if st.button('Save correction and regenerate'):
        try:
            store.revise(r['id'], r['version'], transcript=text)
            st.rerun()
        except Exception as exc:
            st.error(str(exc))
    st.subheader('Clinical findings')
    st.caption('Unlisted concepts are not mentioned, never assumed negative. This limited rule baseline may miss concepts; review the full transcript.')
    facts = a['findings']
    st.dataframe([{k:v for k,v in f.items() if k not in ('evidence','mention')} for f in facts], hide_index=True)
    if facts:
        idx = st.selectbox('Inspect a finding', range(len(facts)), format_func=lambda i: f"{facts[i]['entity']} · {facts[i]['polarity']} · {facts[i]['subject']}")
        e = facts[idx]['mention']
        t = a['transcript']
        st.markdown('<div style="padding:20px;background:white;white-space:pre-wrap">'+html.escape(t[:e['start']])+'<mark>'+html.escape(t[e['start']:e['end']])+'</mark>'+html.escape(t[e['end']:])+'</div>', unsafe_allow_html=True)
        st.caption(f"Exact evidence: {e['speaker']} · [{e['start']}, {e['end']})")
elif page == 'SOAP Note':
    r = current()
    st.caption(f"Version {r['version']} · {'Approved' if r['approved'] else 'Draft — review required'} · {r['analysis']['provider']}")
    st.info('Strict grounding: preserve exact source sentences and speaker labels. Rephrased or added claims are flagged and block approval; correct the transcript to regenerate when necessary.')
    with st.form('note'):
        values = {s: st.text_area(label, r['analysis']['note'][s], height=150) for s,label in [('S','Subjective'),('O','Objective'),('A','Assessment'),('P','Plan')]}
        if st.form_submit_button('Save new version and validate'):
            try:
                store.revise(r['id'], r['version'], note=Note(**values))
                st.rerun()
            except Exception as exc:
                st.error(str(exc))
elif page == 'Validation and Review':
    r = current()
    st.caption(f"Version {r['version']} · {r['edit_count']} edits · processing {r['analysis']['processing_seconds']:.4f}s")
    warnings(r)
    with st.expander('Review complete note', expanded=True):
        for s,t in r['analysis']['note'].items():
            st.markdown('**'+s+'**')
            st.text(t)
    reviewer = st.text_input('Reviewer name (fictional demo identity)')
    ack = st.checkbox('I reviewed all sections and acknowledge the displayed warnings.')
    if st.button('Approve this version', type='primary', disabled=not (reviewer.strip() and ack)):
        try:
            store.approve(r['id'], r['version'], reviewer, ack, time.monotonic()-st.session_state['review_start_'+r['id']])
            st.success('This version is approved for prototype export.')
        except Exception as exc:
            st.error(str(exc))
elif page == 'History and Export':
    st.dataframe(rows, hide_index=True, use_container_width=True)
    r = current()
    if r['approved']:
        for kind in ['json','pdf','docx']:
            payload,mime = export(r, kind)
            st.download_button('Download '+kind.upper(), payload, file_name=f"aci-{r['id'][:8]}-v{r['version']}.{kind}", mime=mime)
    else:
        st.warning('Approve the current note version in Validation and Review before exporting.')
    st.json(r, expanded=False)
