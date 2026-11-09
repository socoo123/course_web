"""Small source/route checks for this worker only; not a build or Go test."""
import hashlib
import json
import re
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
COURSE = ROOT.parent
manifest = json.loads((HERE / 'manifest-fragment.json').read_text())
ids = set()
for source in manifest['sources']:
    assert source['id'].startswith('p8-go-') and source['id'] not in ids
    ids.add(source['id'])
    for key in ['file', 'url', 'sha256', 'retrieved_at', 'last_modified', 'status', 'scope', 'license', 'read_pages', 'visual_pages']:
        assert key in source, (source['id'], key)
    assert hashlib.sha256((ROOT / source['file']).read_bytes()).hexdigest() == source['sha256']
original = next(s for s in manifest['sources'] if s['id'] == 'p8-go-cacm-original')
assert original['url'] == 'https://cacm.acm.org/magazines/2022/5/260357-the-go-programming-language-and-environment/fulltext'
assert original['status'] == 'blocked'
folder = COURSE / 'lectures/update-go-patterns'
assert not (folder / 'draft.zh.md').exists()
routes = 0
for file in folder.glob('*.md'):
    text = file.read_text()
    assert text.startswith('---\n') and text.count('```') % 2 == 0
    assert '## 引用与来源' in text
    assert text.count('<details>') == text.count('</details>')
    for lecture, view in re.findall(r'#/c/mit-6\.824-2021/lec/([^?\s)]+)\?v=(notes|draft|materials)', text):
        assert (COURSE / 'lectures' / lecture / f'{view}.zh.md').exists(), (lecture, view)
        routes += 1
    assert not re.search(r'!\[', text), 'No images planned for this package'
result = f'PASS: {len(ids)} unique source IDs and local source hashes; {routes} lecture links; two Markdown documents/frontmatter/fences/details; exact original CACM URL and blocked status; no draft or image assets.\nNo Go execution, race-detector execution, lab tests, build, or git operations.\n'
(HERE / 'local-check.txt').write_text(result)
print(result)
