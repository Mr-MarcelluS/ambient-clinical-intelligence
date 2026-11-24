import json
from pathlib import Path
from praatio import textgrid


def main():
    records = []
    for i in range(1,4):
        prefix = f'day1_consultation{i:02}'
        turns = []
        for speaker in ['doctor','patient']:
            grid = textgrid.openTextgrid(f'data/raw/primock57/transcripts/{prefix}_{speaker}.TextGrid', includeEmptyIntervals=False)
            for tier in grid.tiers:
                for entry in tier.entries:
                    if hasattr(entry,'label') and entry.label.strip():
                        turns.append({'speaker':speaker.title(),'start':entry.start,'end':entry.end,'text':entry.label})
        turns.sort(key=lambda t:t['start'])
        records.append({'id':prefix,'fictional':True,'turns':turns,
                        'transcript':'\n'.join(t['speaker']+': '+t['text'] for t in turns)})
    Path('data/processed/primock57.json').write_text(json.dumps(records,indent=2))
    print(f'Processed {len(records)} mock consultations with {sum(len(r["turns"]) for r in records)} turns.')


if __name__=='__main__':
    main()
