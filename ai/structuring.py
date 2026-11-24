"""Source-grounded grouping. Lists contain evidence, never inferred absence."""
import re
from backend.schemas import Finding, Utterance


def structure(findings: list[Finding], units: list[Utterance]) -> dict:
    groups={key:[] for key in ['symptoms','medical_history','medication_history','allergies',
                               'relevant_negatives','examination_findings','vital_signs','assessment','plan','follow_up']}
    for f in findings:
        if f.category=='symptom':
            groups['symptoms'].append(f.model_dump())
        if f.polarity=='negative':
            groups['relevant_negatives'].append(f.model_dump())
    for unit in units:
        text=unit.evidence.text
        evidence=unit.evidence.model_dump()
        if unit.section=='O':
            groups['examination_findings'].append(evidence)
            if re.search(r'\b(temperature|blood pressure|pulse|heart rate|oxygen)\b',text,re.I):
                groups['vital_signs'].append(evidence)
        if unit.section=='A':
            groups['assessment'].append(evidence)
        if unit.section=='P':
            groups['plan'].append(evidence)
            if re.search(r'\b(return|follow.up)\b',text,re.I):
                groups['follow_up'].append(evidence)
        if re.search(r'\b(allerg\w*|allergy)\b',text,re.I):
            groups['allergies'].append(evidence)
        elif unit.section=='S' and any(f.category=='medication' and f.evidence==unit.evidence for f in findings):
            groups['medication_history'].append(evidence)
        if re.search(r'\b(history|previously|father|mother|sister|brother)\b',text,re.I):
            groups['medical_history'].append(evidence)
    return groups
