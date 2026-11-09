"""Fetch only the new FAQ; verify and render the three frozen shared sources."""
from pathlib import Path
from datetime import datetime, timezone
import hashlib
import json
import urllib.request
import fitz

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
old = json.loads((ROOT / 'manifest.json').read_text())['sources']
ids = ['lec21-notes-1-2026', 'lec21-notes-2-2026', 'lec21-reading-3-2026']
records = []
for source_id in ids:
    record = next(x for x in old if x['id'] == source_id)
    path = ROOT / record['file']
    assert hashlib.sha256(path.read_bytes()).hexdigest() == record['sha256']
    records.append(record)
    if path.suffix == '.pdf':
        doc = fitz.open(path)
        stem = 'slides' if '65840' in path.name else 'paper'
        (HERE / f'{stem}.txt').write_text('\n'.join(
            f'\n===== PDF PAGE {i + 1} =====\n' + page.get_text()
            for i, page in enumerate(doc)))
        output = HERE / 'rendered'
        output.mkdir(exist_ok=True)
        for i, page in enumerate(doc):
            page.get_pixmap(matrix=fitz.Matrix(1.35, 1.35)).save(output / f'{stem}-{i+1:02}.png')
        print(stem, len(doc), 'pages')
url = 'https://pdos.csail.mit.edu/6.824/papers/bft-faq.txt'
with urllib.request.urlopen(url, timeout=60) as response:
    data = response.read()
    record = dict(id='p8-bft-faq', url=url, final_url=response.url,
                  retrieved_at=datetime.now(timezone.utc).isoformat(),
                  last_modified=response.headers.get('Last-Modified'),
                  http_status=response.status, file='p8-bft/bft-faq.txt',
                  sha256=hashlib.sha256(data).hexdigest(), status='fetched')
(HERE / 'bft-faq.txt').write_bytes(data)
(HERE / 'acquisition.json').write_text(json.dumps(
    {'reused': records, 'new': record}, indent=2) + '\n')
print('three frozen hashes verified; FAQ:', record)
