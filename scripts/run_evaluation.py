"""Measure against independent authored labels. Never substitutes predictions for gold."""
import json
from collections import Counter
from pathlib import Path
from backend.pipeline import analyze


def score(gold, pred):
    tp = sum((gold & pred).values())
    p = tp/sum(pred.values()) if pred else 0
    r = tp/sum(gold.values()) if gold else 0
    return {'precision':p, 'recall':r, 'f1':2*p*r/(p+r) if p+r else 0,
            'gold':sum(gold.values()),'predicted':sum(pred.values()),'correct':tp}


def main():
    records = [json.loads(line) for line in Path('data/synthetic/consultations.jsonl').read_text().splitlines()]
    reports = {}
    for split in ['development','validation','test']:
        subset = [r for r in records if r['split']==split]
        gold, pred = {k:Counter() for k in ['symptoms','medications','duration','negation','uncertainty','subject','exact_span']}, {k:Counter() for k in ['symptoms','medications','duration','negation','uncertainty','subject','exact_span']}
        section_matches = preserved = total_facts = unsupported = total_pred = contradictions = 0
        processing = []
        span_supported = span_total = gold_lines = preserved_lines = negative_total = negative_preserved = 0
        failures = []
        for record in subset:
            a = analyze(record['transcript'])
            processing.append(a.processing_seconds)
            note_text = '\n'.join(a.note.model_dump().values())
            for section, gold_text in record['expected_soap'].items():
                for line in gold_text.splitlines():
                    gold_lines += 1
                    preserved_lines += int(line in a.note.model_dump()[section])
            for f in a.findings:
                span_total += 1
                span_supported += int(a.transcript[f.evidence.start:f.evidence.end] == f.evidence.text and a.transcript[f.mention.start:f.mention.end] == f.mention.text)
            for f in record['expected_entities']:
                if f['polarity'] == 'negative':
                    negative_total += 1
                    # Verify the entire gold source turn containing this span is retained.
                    start = record['transcript'].rfind('\n', 0, f['start']) + 1
                    end = record['transcript'].find('\n', f['end'])
                    line = record['transcript'][start:end if end >= 0 else len(record['transcript'])]
                    content = line.split(': ', 1)[-1]
                    negative_preserved += int(content in note_text)

            for actual, bucket in [(record['expected_entities'],gold),([f.model_dump() | {'start':f.mention.start,'end':f.mention.end} for f in a.findings],pred)]:
                for f in actual:
                    base = (record['id'],f['entity'],f['start'])
                    if f['category']=='symptom':
                        bucket['symptoms'][base]+=1
                    if f['category']=='medication':
                        bucket['medications'][base]+=1
                    if f['duration']:
                        bucket['duration'][base+(f['duration'],)]+=1
                    if f['polarity']=='negative':
                        bucket['negation'][base]+=1
                    if f['polarity']=='uncertain':
                        bucket['uncertainty'][base]+=1
                    bucket['subject'][base+(f['subject'],)]+=1
                    bucket['exact_span'][base+(f['end'],)]+=1
            section_matches += sum(a.note.model_dump()[s]==record['expected_soap'][s] for s in ['S','O','A','P'])
            text='\n'.join(a.note.model_dump().values())
            for f in record['expected_entities']:
                total_facts+=1
                preserved+=int(f['source_span'] in text)
            unsupported+=sum(w.code=='unsupported_claim' for w in a.warnings)
            total_pred+=sum(len(t.splitlines()) for t in a.note.model_dump().values())
            contradictions+=sum(w.code=='contradiction' for w in a.warnings)
            if [(f.entity,f.polarity) for f in a.findings]!=[(f['entity'],f['polarity']) for f in record['expected_entities']]:
                failures.append(record['id'])
        reports[split]={'records':len(subset),'metrics':{k:score(gold[k],pred[k]) for k in gold},
            'soap_section_exact_accuracy':section_matches/(4*len(subset)),
            'soap_entity_surface_coverage':preserved/total_facts if total_facts else None,
            'soap_gold_line_completeness':preserved_lines/gold_lines,
            'soap_negative_turn_verbatim_preservation':negative_preserved/negative_total if negative_total else None,
            'evidence_coverage':span_supported/span_total if span_total else None,
            'unsupported_extraction_span_rate':1-span_supported/span_total if span_total else None,
            'unsupported_generated_line_rate':unsupported/total_pred,
            'input_contradiction_warnings':contradictions,
            'mean_processing_seconds':sum(processing)/len(processing),
            'polarity_mismatch_records':failures}
    result={'method':'Author-labeled synthetic family-disjoint evaluation; no clinician verification. Surface coverage is not semantic accuracy.',
            'results':reports}
    Path('data/evaluation/metrics.json').write_text(json.dumps(result,indent=2))
    lines=['# Evaluation report','',result['method'],'', '| Split | Cases | Symptom F1 | Negation F1 | Uncertainty F1 | Section exact | Mean seconds |','|---|---:|---:|---:|---:|---:|---:|']
    for split,r in reports.items():
        m=r['metrics']
        lines.append(f"| {split} | {r['records']} | {m['symptoms']['f1']:.3f} | {m['negation']['f1']:.3f} | {m['uncertainty']['f1']:.3f} | {r['soap_section_exact_accuracy']:.3f} | {r['mean_processing_seconds']:.6f} |")
    lines += ['', 'Full precision, recall, F1 and denominators for medications, duration, subjects and exact spans are in `data/evaluation/metrics.json`.',
              '', 'The 100 cases are 20 scenario families with five numeric variants each; effective linguistic diversity is 20, not 100. Families are disjoint across splits. No training or fine-tuning was performed. Gold labels are independently specified in the data generator, not produced by the extractor. They have not been manually verified by an independent human or clinician.',
              '', 'Held-out failures are retained and reported, not used to tune the rules. Postposed negation ("Fever is absent") is a known extraction failure. Exact quotations preserve it in the note, but the structured polarity label can be wrong.',
              '', 'SOAP is extractive: exact section matching and surface coverage do not establish clinical adequacy or semantic validation. Unsupported line checking deliberately rejects valid paraphrases. No human review time savings are claimed. Review durations recorded in smoke tests are not an efficiency study.']
    Path('docs/evaluation_report.md').write_text('\n'.join(lines)+'\n')
    print(json.dumps(reports['test'],indent=2))


if __name__=='__main__':
    main()
