"""Complete fictional consultation recording -> ASR -> corrected SOAP draft.

Correction uses the known authored script for this demonstration only, never as an ASR prediction.
The resulting note is deliberately not automatically approved.
"""
import json
import os
import subprocess
from pathlib import Path
from ai.speech import transcribe
from backend.pipeline import analyze

TRANSCRIPT = '''Patient: I have a headache for three days, but no fever or vomiting.
Doctor: On examination, temperature is 37 degrees.
Doctor: My assessment is a possible migraine.
Doctor: Plan: rest and return in two days if symptoms persist.'''


def main():
    root=Path('data/synthetic/audio')
    root.mkdir(parents=True,exist_ok=True)
    root.joinpath('consultation.reference.txt').write_text(TRANSCRIPT)
    spoken=' '.join(line.split(': ',1)[1] for line in TRANSCRIPT.splitlines())
    target=root/'consultation.wav'
    subprocess.run([os.getenv('ACI_ESPEAK','espeak-ng'),'-s','140','-v','en-us','-w',str(target),spoken],check=True)
    result=transcribe(target)
    root.joinpath('consultation.asr.json').write_text(json.dumps(result,indent=2))
    root.joinpath('consultation.raw-soap.json').write_text(analyze(result['transcript']).model_dump_json(indent=2))
    root.joinpath('consultation.corrected-soap.json').write_text(analyze(TRANSCRIPT).model_dump_json(indent=2))
    print('Generated complete fictional audio and separate raw/corrected SOAP drafts. Neither is clinically approved.')


if __name__=='__main__':
    main()
