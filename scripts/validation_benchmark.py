import json
from pathlib import Path
from backend.pipeline import analyze
from ai.validation import validate


def main():
    a=analyze('Patient: I have headache for three days. I take metformin 500 mg daily. My father has diabetes.\nDoctor: On examination, temperature is 37 degrees.')
    changes=[('invented_diagnosis','A','[Doctor] Diagnosis: pneumonia.'),
             ('invented_medication','P','[Doctor] Start amoxicillin 500 mg.'),
             ('invented_exam','O','[Doctor] Lungs are clear.'),
             ('polarity_reversal','S','[Patient] I have no headache for three days.'),
             ('wrong_duration','S','[Patient] I have headache for ten days.'),
             ('wrong_dose','S','[Patient] I take metformin 1000 mg daily.'),
             ('wrong_subject','S','[Patient] I have diabetes.'),
             ('wrong_speaker','O','[Patient] On examination, temperature is 37 degrees.')]
    tests=[]
    for name,section,value in changes:
        note=a.note.model_copy(update={section:value})
        warnings=validate(a.transcript,a.findings,a.utterances,note)
        tests.append({'case':name,'detected':any(w.code=='unsupported_claim' for w in warnings)})
    base_errors=sum(w.severity=='error' for w in a.warnings)
    result={'cases':tests,'detection_rate':sum(t['detected'] for t in tests)/len(tests),
            'unmodified_note_error_count':base_errors,
            'scope':'Eight authored mutations detected by conservative exact-line matching; not semantic hallucination detection.'}
    Path('data/evaluation/validation_metrics.json').write_text(json.dumps(result,indent=2))
    print(json.dumps(result,indent=2))


if __name__=='__main__':
    main()
