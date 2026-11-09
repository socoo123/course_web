"""Archive P8 Go sources and extract the two supplied PDF snapshots; no Go execution."""
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

import fitz
import requests

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent


def fetch(source_id, url, filename):
    started = datetime.now(timezone.utc).isoformat()
    try:
        response = requests.get(url, timeout=60)
        target = HERE / filename
        target.write_bytes(response.content)
        record = dict(id=source_id, url=url, final_url=response.url,
                      retrieved_at=started, last_modified=response.headers.get('Last-Modified'),
                      http_status=response.status_code, file=str(target.relative_to(ROOT)),
                      sha256=hashlib.sha256(response.content).hexdigest(),
                      status='fetched' if response.ok else 'blocked')
        (HERE / (filename + '.headers.json')).write_text(json.dumps(dict(response.headers), indent=2))
    except requests.RequestException as exc:
        record = dict(id=source_id, url=url, final_url=None, retrieved_at=started,
                      last_modified=None, file=None, sha256=None, status='blocked', error=str(exc))
    return record


if __name__ == '__main__':
    records = [fetch('p8-go-faq-2026', 'https://pdos.csail.mit.edu/6.824/papers/go-faq.txt', 'go-faq-2026.txt'),
               fetch('p8-go-cacm-original', 'https://cacm.acm.org/magazines/2022/5/260357-the-go-programming-language-and-environment/fulltext', 'cacm-original.html')]
    (HERE / 'fetch-records.json').write_text(json.dumps(records, ensure_ascii=False, indent=2) + '\n')
    for year, filename in [(2026, 'update-2026-Go-MIT6824-2026.pdf'), (2021, 'mit-6824-go-2021.pdf')]:
        doc = fitz.open(ROOT / filename)
        pages = [dict(page=i+1, text=page.get_text(sort=True)) for i, page in enumerate(doc)]
        (HERE / f'slides-{year}.txt').write_text('\n'.join(f'\n=== PDF PAGE {p["page"]} ===\n{p["text"]}' for p in pages))
        (HERE / f'slides-{year}.json').write_text(json.dumps(pages, ensure_ascii=False, indent=2))
        print(year, len(doc), doc.metadata)
    print(json.dumps(records, ensure_ascii=False, indent=2))
