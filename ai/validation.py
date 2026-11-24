import re
from backend.schemas import Finding, Note, Utterance, Warning
from ai.soap import MISSING, rendered


def validate(transcript: str, findings: list[Finding], units: list[Utterance], note: Note) -> list[Warning]:
    warnings = []
    for f in findings:
        for span in [f.evidence, f.mention]:
            if transcript[span.start:span.end] != span.text:
                warnings.append(Warning(code='source_mismatch', reason=f'Invalid source span for {f.entity}.', severity='error', evidence=[span]))
    for section, text in note.model_dump().items():
        expected = [u for u in units if u.section == section]
        allowed = {rendered(u): u for u in expected}
        if not expected:
            warnings.append(Warning(code='missing_information', reason=MISSING[section], severity='info'))
        for line in text.splitlines():
            if line.strip() and line not in allowed and not (not expected and line == MISSING[section]):
                warnings.append(Warning(code='unsupported_claim', reason=f'{section}: text is not an exact, attributed source statement in this section: {line}', severity='error'))
        for line, unit in allowed.items():
            if line not in text.splitlines():
                warnings.append(Warning(code='omitted_evidence', reason=f'{section}: source statement omitted or changed.', evidence=[unit.evidence]))
    for i, f in enumerate(findings):
        for other in findings[i+1:]:
            if f.entity == other.entity and f.subject == other.subject and {f.polarity, other.polarity} == {'positive', 'negative'}:
                temporal = f.temporality != other.temporality and 'unspecified' not in (f.temporality, other.temporality)
                warnings.append(Warning(code='temporal_change' if temporal else 'contradiction',
                    reason=f'{f.entity}: different polarity statements; review chronology and context.', evidence=[f.evidence, other.evidence]))
    for unit in units:
        if re.search(r'\b(sorry|I mean|correction|actually)\b', unit.evidence.text, re.I):
            warnings.append(Warning(code='correction', reason='Explicit correction; review preceding statement.', evidence=[unit.evidence]))
        if unit.evidence.speaker == 'Unknown':
            warnings.append(Warning(code='unknown_speaker', reason='Assign speaker labels before interpreting attribution.', evidence=[unit.evidence]))
    return warnings
