"""Lossless caption reading groups and PDF page artifacts (local sources only)."""
import json
import subprocess
from itertools import groupby
from pathlib import Path
import fitz

ROOT = Path(__file__).parent
events = json.loads((ROOT/'video.en-orig.json3').read_text())['events']
cues = []
for event in events:
    text = ''.join(s.get('utf8','') for s in event.get('segs',[])).strip()
    if text:
        cues.append(dict(start_ms=event['tStartMs'], end_ms=event['tStartMs']+event.get('dDurationMs',0), text=text))
(ROOT/'captions.normalized.json').write_text(json.dumps(cues,ensure_ascii=False,indent=2)+'\n')
groups = []
for minute, group in groupby(enumerate(cues,1), lambda pair: pair[1]['start_ms']//60000):
    items = list(group)
    groups.append(f'[{minute:02}:00] cues {items[0][0]}–{items[-1][0]}\n'+ ' '.join(c['text'] for _,c in items))
assert ' '.join(c['text'] for c in cues) == ' '.join(g.split('\n',1)[1] for g in groups)
(ROOT/'reading-by-minute.txt').write_text('\n\n'.join(groups)+'\n')
subprocess.run(['pdftotext','-layout',str(ROOT/'katabi-analogicfs.pdf'),str(ROOT/'katabi-analogicfs.layout.txt')],check=True)
pages = ROOT/'paper-pages'
pages.mkdir(exist_ok=True)
with fitz.open(ROOT/'katabi-analogicfs.pdf') as doc:
    for i,page in enumerate(doc,1):
        page.get_pixmap(matrix=fitz.Matrix(1.5,1.5)).save(pages/f'page-{i:02}.png')
print(f'{len(cues)} cues; {len(groups)} minute groups; {len(doc)} pages' if not doc.is_closed else f'{len(cues)} cues; {len(groups)} minute groups; PDF rendered')
