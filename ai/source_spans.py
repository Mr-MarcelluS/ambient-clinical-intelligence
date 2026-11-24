"""Attach segment-level times only when the text exactly matches the original ASR."""
from backend.schemas import Analysis
from ai.structuring import structure


def attach_segment_times(analysis: Analysis, segments: list[dict]) -> Analysis:
    if ' '.join(s['text'] for s in segments) != analysis.transcript:
        return analysis  # Edited text must not inherit misleading audio alignment.
    ranges=[]
    cursor=0
    for segment in segments:
        end=cursor+len(segment['text'])
        ranges.append((cursor,end,segment['start']))
        cursor=end+1
    spans=[u.evidence for u in analysis.utterances]
    spans += [span for f in analysis.findings for span in [f.evidence,f.mention]]
    for span in spans:
        for start,end,timestamp in ranges:
            if span.start < end and span.end > start:
                span.timestamp=timestamp
                break
    analysis.structured=structure(analysis.findings,analysis.utterances)
    return analysis
