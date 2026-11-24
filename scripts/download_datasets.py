"""Download a bounded, explicitly licensed mock-consultation subset; never restricted data."""
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
import httpx


def main():
    cfg = json.loads(Path('data/manifests/sources.json').read_text())
    root = Path('data/raw/primock57')
    root.mkdir(parents=True, exist_ok=True)
    manifest = {'dataset':'PriMock57 subset', 'source':cfg['source'], 'license':'CC-BY-4.0',
                'download_date':datetime.now(timezone.utc).isoformat(), 'files':[],
                'intended_usage':'mock dialogue structure inspection; no model training',
                'restrictions':'attribution; retain license; indicate adaptations', 'processing_steps':['UTF-8 decode', 'JSON parse or TextGrid parse']}
    with httpx.Client(follow_redirects=True, timeout=60) as client:
        revision = client.get('https://api.github.com/repos/babylonhealth/primock57/commits/main').raise_for_status().json()['sha']
        manifest['revision'] = revision
        for path in cfg['files']:
            url = f'https://raw.githubusercontent.com/babylonhealth/primock57/{revision}/{path}'
            response = client.get(url)
            response.raise_for_status()
            content = response.content
            if len(content) > 5*1024*1024:
                raise ValueError('Unexpectedly large text file')
            text = content.decode('utf-8')
            dest = root/path
            dest.parent.mkdir(parents=True, exist_ok=True)
            dest.write_bytes(content)
            if path.endswith('.json'):
                json.loads(text)
            elif path.endswith('.TextGrid'):
                from praatio import textgrid
                textgrid.openTextgrid(str(dest), includeEmptyIntervals=False)
            manifest['files'].append({'path':path,'url':url,'bytes':len(content),'sha256':hashlib.sha256(content).hexdigest()})
    manifest['number_of_consultations'] = 3
    Path('data/manifests/primock57.json').write_text(json.dumps(manifest, indent=2))
    print(f"Validated {len(manifest['files'])} files at revision {revision}")


if __name__ == '__main__':
    main()
