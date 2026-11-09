"""Lossless ASR grouping, bounded paper extraction/rendering, snapshot comparison."""
import difflib
import json
from pathlib import Path
import fitz

root=Path(__file__).parent
out=root/'captions'
out.mkdir(exist_ok=True)
cues=[]
for e in json.loads((root/'video.en-orig.json3').read_text())['events']:
    text=''.join(s.get('utf8','') for s in e.get('segs',[])).strip()
    if text:
        cues.append(dict(start_ms=e['tStartMs'],end_ms=e['tStartMs']+e.get('dDurationMs',0),text=text))
(out/'captions.normalized.json').write_text(json.dumps(cues,ensure_ascii=False,indent=2)+'\n')
groups={}
for c in cues:
    groups.setdefault(c['start_ms']//60000,[]).append(c['text'])
assert ' '.join(' '.join(v) for v in groups.values())==' '.join(c['text'] for c in cues)
(out/'reading-by-minute.txt').write_text('\n\n'.join(f'[{m:02d}:00]\n'+' '.join(v) for m,v in groups.items())+'\n')
(out/'transcript.en.txt').write_text('\n'.join(f"[{c['start_ms']/1000:.3f}–{c['end_ms']/1000:.3f}] {c['text']}" for c in cues)+'\n')
doc=fitz.open(root/'li-sundr.pdf')
(root/'paper-pages').mkdir(exist_ok=True)
# Assigned prefix ends before section 3.4 on page 6; pages 6–7 also support partial concurrency review.
for i in range(min(7,len(doc))):
    p=doc[i]
    (root/f'paper-page-{i+1:02d}.txt').write_text(p.get_text())
    p.get_pixmap(matrix=fitz.Matrix(1.4,1.4)).save(root/'paper-pages'/f'page-{i+1:02d}.png')
a=(root/'l-sundr.txt').read_text().splitlines(True)
b=(root.parent/'update-2026-l-sundr.txt').read_text().splitlines(True)
(root/'lecture-2021-2026.diff.txt').write_text(''.join(difflib.unified_diff(a,b,fromfile='2021/l-sundr.txt',tofile='2026/l-sundr.txt')))
print(f'{len(cues)} cues; {len(doc)} PDF pages; first={cues[0]["start_ms"]}; last={cues[-1]["end_ms"]}')
print('paper bytes identical:',(root/'li-sundr.pdf').read_bytes()==(root.parent/'update-2026-li-sundr.pdf').read_bytes())
