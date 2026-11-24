import json
from pathlib import Path


def main():
    records=[json.loads(x) for x in Path('data/synthetic/consultations.jsonl').read_text().splitlines()]
    assert len(records)>=50
    assert len({r['id'] for r in records})==len(records)
    families={s:{r['family'] for r in records if r['split']==s} for s in ['development','validation','test']}
    assert not families['development'] & (families['validation']|families['test'])
    assert not families['validation'] & families['test']
    for r in records:
        assert r['fictional'] is True
        for f in r['expected_entities']:
            assert r['transcript'][f['start']:f['end']]==f['source_span']
    print(f'{len(records)} records validated; exact spans and disjoint families confirmed.')


if __name__=='__main__':
    main()
