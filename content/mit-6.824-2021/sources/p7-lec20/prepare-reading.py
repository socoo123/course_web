"""Preserve every caption text in sequence; extract and render the assigned PDF."""
import json
import subprocess
from pathlib import Path
import fitz

root = Path(__file__).parent
subprocess.run(['python3','/Users/zy/.config/opencode/skills/technical-video-notes/scripts/normalize_captions.py',str(root/'video.en-orig.json3'),str(root/'captions')],check=True)
cues = json.loads((root/'captions/captions.normalized.json').read_text())
groups = {}
for cue in cues:
    groups.setdefault(cue['start_ms']//60000,[]).append(cue['text'])
assert ' '.join(' '.join(v) for v in groups.values()) == ' '.join(c['text'] for c in cues)
(root/'captions/reading-by-minute.txt').write_text('\n\n'.join(f'[{m:02d}:00]\n'+' '.join(v) for m,v in groups.items())+'\n')
subprocess.run(['pdftotext','-layout',str(root/'blockstack-atc16.pdf'),str(root/'blockstack-atc16.layout.txt')],check=True)
doc = fitz.open(root/'blockstack-atc16.pdf')
(root/'paper-pages').mkdir(exist_ok=True)
for i,page in enumerate(doc):
    page.get_pixmap(matrix=fitz.Matrix(1.4,1.4)).save(root/'paper-pages'/f'page-{i+1:02d}.png')
print(f'{len(cues)} cues; {len(groups)} minute groups; {len(doc)} PDF pages')
