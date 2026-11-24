"""Author-specified gold labels, independent of extractor. Split by scenario family."""
import json
from pathlib import Path

# Each turn has an explicit gold SOAP section. Facts are (surface, category, polarity, subject, duration, dose).
CASES = [
('headache', [('Patient','S','I have a headache for {d} days, but no fever or vomiting.')], [('headache','symptom','positive','patient','{d} days',None),('fever','symptom','negative','patient',None,None),('vomiting','symptom','negative','patient',None,None)]),
('cough', [('Patient','S','I have a cough and a sore throat for {d} days.'),('Doctor','O','On examination, lungs are clear.')], [('cough','symptom','positive','patient','{d} days',None),('sore throat','symptom','positive','patient','{d} days',None)]),
('gastrointestinal', [('Patient','S','I have nausea for {d} days. I deny diarrhea.')], [('nausea','symptom','positive','patient','{d} days',None),('diarrhea','symptom','negative','patient',None,None)]),
('injury', [('Patient','S','There is swelling for {d} days.'),('Doctor','P','Plan: rest and return in a week.')], [('swelling','symptom','positive','patient','{d} days',None)]),
('fatigue', [('Patient','S','I think I have fatigue for {d} days.')], [('fatigue','symptom','uncertain','patient','{d} days',None)]),
('joint', [('Patient','S','I have joint pain for {d} days. No rash.')], [('joint pain','symptom','positive','patient','{d} days',None),('rash','symptom','negative','patient',None,None)]),
('followup', [('Patient','S','My cough is still present for {d} days.'),('Doctor','P','Follow-up in one week.')], [('cough','symptom','positive','patient','{d} days',None)]),
('medication', [('Patient','S','I take metformin {dose} mg twice daily.')], [('metformin','medication','positive','patient',None,'{dose} mg')]),
('general', [('Patient','S','I have no concerns today.'),('Doctor','O','Blood pressure is 120 over 80.')], []),
('family', [('Patient','S','My father has diabetes. I have fatigue for {d} days.')], [('diabetes','condition','positive','father',None,None),('fatigue','symptom','positive','patient','{d} days',None)]),
('assessment', [('Patient','S','I have a headache for {d} days.'),('Doctor','A','My assessment is possible migraine.')], [('headache','symptom','positive','patient','{d} days',None),('migraine','condition','uncertain','patient',None,None)]),
('plan', [('Doctor','P','Plan: take paracetamol {dose} mg once daily.')], [('paracetamol','medication','positive','patient',None,'{dose} mg')]),
('temporal', [('Patient','S','I had fever yesterday, but no fever today. The cough lasted {d} days.')], [('fever','symptom','positive','patient',None,None),('fever','symptom','negative','patient',None,None),('cough','symptom','positive','patient','{d} days',None)]),
('correction', [('Patient','S','I have pain for one day. Sorry, I mean {d} days.')], [('pain','symptom','positive','patient','one day',None)]),
('contradiction', [('Patient','S','I have fever. I do not have fever. I have a cough for {d} days.')], [('fever','symptom','positive','patient',None,None),('fever','symptom','negative','patient',None,None),('cough','symptom','positive','patient','{d} days',None)]),
('allergy', [('Patient','S','I am allergic to amoxicillin. I have a rash for {d} days.')], [('amoxicillin','medication','positive','patient',None,None),('rash','symptom','positive','patient','{d} days',None)]),
('heldout_uncertainty', [('Patient','S','Perhaps the dizziness began {d} days ago; no chest pain.'),('Doctor','P','Return if symptoms worsen.')], [('dizziness','symptom','uncertain','patient','{d} days',None),('chest pain','symptom','negative','patient',None,None)]),
('heldout_negation', [('Patient','S','I have not experienced nausea or vomiting for {d} days, but I have abdominal pain.')], [('nausea','symptom','negative','patient','{d} days',None),('vomiting','symptom','negative','patient','{d} days',None),('abdominal pain','symptom','positive','patient',None,None)]),
('heldout_subject', [('Patient','S','My mother has asthma. I take cetirizine {dose} mg daily.'),('Doctor','O','Temperature measured at 36.8 degrees.')], [('asthma','condition','positive','mother',None,None),('cetirizine','medication','positive','patient',None,'{dose} mg')]),
('heldout_language', [('Patient','S','The headache has been bothering me for {d} days. Fever is absent.'),('Doctor','A','The diagnosis is uncertain.')], [('headache','symptom','positive','patient','{d} days',None),('fever','symptom','negative','patient',None,None)]),
]


def generate():
    records = []
    missing = {'S':'Subjective information', 'O':'Objective findings', 'A':'Assessment', 'P':'Plan'}
    for family, (name, turns, facts) in enumerate(CASES):
        for variant in range(5):
            values = {'d': variant+2, 'dose': [10,20,50,100,250][variant]}
            turns_f = [(sp,se,tx.format(**values)) for sp,se,tx in turns]
            transcript = '\n'.join(sp+': '+tx for sp,se,tx in turns_f)
            gold = []
            offsets = {}
            for surface,cat,pol,subject,duration,dose in facts:
                start = transcript.lower().index(surface.lower(), offsets.get(surface,0))
                offsets[surface] = start+len(surface)
                gold.append(dict(entity=surface,category=cat,polarity=pol,subject=subject,
                                 duration=duration.format(**values) if duration else None,
                                 dosage=dose.format(**values) if dose else None,
                                 start=start,end=start+len(surface),source_span=transcript[start:start+len(surface)]))
            expected_soap = {s:'\n'.join(f'[{sp}] {tx}' for sp,se,tx in turns_f if se == s) or label+' not documented.' for s,label in missing.items()}
            safety = {'temporal':['temporal_change'], 'correction':['correction'], 'contradiction':['contradiction']}.get(name, [])
            records.append(dict(id=f'syn-{family:02}-{variant}', fictional=True, family=name,
                split='development' if family<12 else 'validation' if family<16 else 'test',
                transcript=transcript, speakers=[sp for sp,_,_ in turns_f], expected_entities=gold,
                expected_soap=expected_soap, expected_missing=[s for s in missing if not any(se==s for _,se,_ in turns_f)],
                expected_safety_warnings=safety, annotation_status='author-specified, not clinician-verified'))
    root = Path('data/synthetic')
    root.mkdir(parents=True, exist_ok=True)
    (root/'consultations.jsonl').write_text('\n'.join(json.dumps(r) for r in records)+'\n')
    print(f'Wrote {len(records)} fictional cases; family-disjoint split 60/20/20.')


if __name__ == '__main__':
    generate()
