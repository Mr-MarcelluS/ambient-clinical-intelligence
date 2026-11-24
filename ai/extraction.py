"""Conservative English rule baseline. Offsets always address the original text."""
import re
from backend.schemas import Finding, Span, Utterance

TERMS = {
    'symptom': ['headache', 'fever', 'vomiting', 'nausea', 'cough', 'fatigue', 'diarrhea',
                'diarrhoea', 'dizziness', 'chest pain', 'shortness of breath', 'joint pain',
                'abdominal pain', 'sore throat', 'runny nose', 'pain', 'swelling', 'rash', 'bleeding'],
    'condition': ['diabetes', 'hypertension', 'asthma', 'migraine', 'pneumonia', 'infection'],
    'medication': ['paracetamol', 'acetaminophen', 'ibuprofen', 'metformin', 'amoxicillin',
                   'aspirin', 'lisinopril', 'salbutamol', 'cetirizine'],
}
TERM_CATEGORY = {term: category for category, terms in TERMS.items() for term in terms}
PATTERN = re.compile(r'\b(?:' + '|'.join(sorted(TERM_CATEGORY, key=len, reverse=True)) + r')\b', re.I)
NEG = re.compile(r"\b(?:no|not|denies|deny|without|never|haven't|hasn't|don't|doesn't|didn't)\b", re.I)
UNCERTAIN = re.compile(r'\b(?:maybe|might|may|possibly|perhaps|think|unsure|suspect|possible|around|about)\b', re.I)
DURATION = re.compile(r'\b(?:\d+|one|two|three|four|five|six|seven|a|several)(?: or (?:\d+|three))? (?:hours?|days?|weeks?|months?|years?)\b', re.I)
DOSAGE = re.compile(r'\b\d+(?:\.\d+)?\s*(?:mg|mcg|g|ml|units)\b', re.I)
FREQUENCY = re.compile(r'\b(?:once daily|twice daily|three times daily|daily|as needed|every \d+ hours)\b', re.I)


def classify(text: str, speaker: str) -> str:
    if speaker != 'Doctor':
        return 'S'
    low = text.lower()
    if re.search(r'\b(?:assessment|diagnosis|impression|suspect|consistent with)\b', low):
        return 'A'
    if re.search(r'\b(?:plan|recommend|take|start|continue|stop|return|follow.up|order|advised|rest|drink|test)\b', low):
        return 'P'
    if re.search(r'\b(?:examination|on exam|temperature|blood pressure|pulse|heart rate|oxygen|measured|lungs|tenderness)\b', low):
        return 'O'
    return 'S'


def utterances(transcript: str) -> list[Utterance]:
    result = []
    for line in re.finditer(r'[^\n]+', transcript):
        raw = line.group()
        label = re.match(r'\s*(Doctor|Patient|Clinician|Unknown):\s*', raw, re.I)
        speaker = label.group(1).title() if label else 'Unknown'
        speaker = 'Doctor' if speaker == 'Clinician' else speaker
        offset = line.start() + (label.end() if label else 0)
        content = transcript[offset:line.end()]
        for sentence in re.finditer(r'(?:[^.!?]|(?<=\d)\.(?=\d))+(?:[.!?]+|$)', content):
            text = sentence.group().strip()
            if not text or text.endswith('?'):
                continue
            start = offset + sentence.start() + len(sentence.group()) - len(sentence.group().lstrip())
            span = Span(start=start, end=start+len(text), text=text, speaker=speaker)
            result.append(Utterance(id=f'u{len(result)}', section=classify(text, speaker), evidence=span))
    return result


def extract(transcript: str) -> tuple[list[Finding], list[Utterance]]:
    if not transcript.strip():
        raise ValueError('Transcript cannot be empty.')
    units = utterances(transcript)
    findings = []
    for unit in units:
        span = unit.evidence
        for clause in re.finditer(r'.+?(?=\bbut\b|\bhowever\b|;|$)', span.text, re.I):
            text = clause.group()
            for match in PATTERN.finditer(text):
                prefix = text[:match.start()]
                # Scope resets at a new explicit first-person assertion.
                scope = re.split(r'\band\s+(?:I|he|she|the patient)\s+', prefix, flags=re.I)[-1]
                uncertain = bool(UNCERTAIN.search(text))
                negative = bool(NEG.search(scope))
                subject_match = re.search(r'\b(?:my|his|her) (father|mother|sister|brother|son|daughter|wife|husband)\b', text, re.I)
                subject = subject_match.group(1).lower() if subject_match else ('unknown' if span.speaker == 'Unknown' else 'patient')
                duration = DURATION.search(text)
                # Attach dosage only to the adjacent medication phrase, never another drug.
                next_term = PATTERN.search(text, match.end())
                suffix = text[match.end():next_term.start() if next_term else len(text)]
                category = TERM_CATEGORY[match.group().lower()]
                dose = DOSAGE.search(suffix) if category == 'medication' else None
                freq = FREQUENCY.search(suffix) if category == 'medication' else None
                temporal = re.search(r'\b(yesterday|today|previously|last week|now)\b', text, re.I)
                start = span.start + clause.start() + match.start()
                findings.append(Finding(
                    id=f'f{len(findings)}', entity=match.group().lower(), category=category,
                    polarity='negative' if negative else 'uncertain' if uncertain else 'positive',
                    certainty='uncertain' if uncertain else 'certain', subject=subject,
                    duration=duration.group() if duration else None, dosage=dose.group() if dose else None,
                    frequency=freq.group() if freq else None,
                    temporality=temporal.group().lower() if temporal else 'unspecified', evidence=span,
                    mention=Span(start=start, end=start+len(match.group()), text=match.group(), speaker=span.speaker)))
    return findings, units


def polarity_for(findings: list[Finding], entity: str) -> list[str]:
    return [f.polarity for f in findings if f.entity == entity] or ['not mentioned']
