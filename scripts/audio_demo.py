"""Generate fictional speech locally with espeak-ng and measure actual ASR output."""
import json
import os
import subprocess
from pathlib import Path
import jiwer
from ai.speech import transcribe
from backend.pipeline import analyze

SAMPLES = [
 'I have a headache for three days. I do not have a fever or vomiting.',
 'I think I have a cough. My father has diabetes. I take metformin five hundred milligrams twice daily.',
 'The pain started yesterday. Sorry, I mean two days ago. I do not have nausea.'
]


def main():
    root=Path('data/synthetic/audio')
    root.mkdir(parents=True,exist_ok=True)
    reports=[]
    normalize=jiwer.Compose([jiwer.ToLowerCase(),jiwer.RemovePunctuation(),jiwer.RemoveMultipleSpaces(),jiwer.Strip()])
    for i,text in enumerate(SAMPLES):
        wav=root/f'demo-{i}.wav'
        subprocess.run([os.getenv('ACI_ESPEAK','espeak-ng'),'-s','145','-v','en-us','-w',str(wav),text],check=True)
        (root/f'demo-{i}.reference.txt').write_text(text)
        result=transcribe(wav)
        (root/f'demo-{i}.asr.json').write_text(json.dumps(result,indent=2))
        note=analyze(result['transcript'])
        (root/f'demo-{i}.soap.json').write_text(note.model_dump_json(indent=2))
        reports.append({'sample':i,'reference':text,'hypothesis':result['transcript'],
                        'wer':jiwer.wer(normalize(text),normalize(result['transcript'])),
                        'processing_seconds':result['processing_seconds'],'audio_seconds':result['audio_seconds']})
    Path('data/evaluation/audio_metrics.json').write_text(json.dumps({'model':os.getenv('ACI_ASR_MODEL','tiny.en'),
        'device':'cpu','compute':'int8','normalization':'lowercase, remove punctuation, collapse whitespace',
        'source':'local espeak-ng synthesis, entirely fictional text; no speaker labels or speaker inference',
        'samples':reports,'mean_wer':sum(r['wer'] for r in reports)/len(reports)},indent=2))
    print(json.dumps(reports,indent=2))


if __name__=='__main__':
    main()
