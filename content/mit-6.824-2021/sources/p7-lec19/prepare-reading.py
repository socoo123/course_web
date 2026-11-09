"""Prepare lossless reading groups and actual PDF page renders; acquire fallback."""
import json
import subprocess
from pathlib import Path
import fitz
from acquire import document

root = Path(__file__).parent
entries = json.loads((root/'acquisition.json').read_text())
if not (root/'nielsen.pdf').exists():
    entry = document(('nielsen.pdf',['https://www.cs.ubc.ca/~bestchai/teaching/cs538b_2014w2/how-bitcoin-actually-works.pdf']))
    entry['url'] = 'http://www.michaelnielsen.org/ddi/how-the-bitcoin-protocol-actually-works'
    entry['relation'] = 'Third-party teaching snapshot of assigned Nielsen essay; original three URL attempts returned404.'
    entries.append(entry)
    (root/'acquisition.json').write_text(json.dumps(entries,indent=2)+'\n')
subprocess.run(['python3','/Users/zy/.config/opencode/skills/technical-video-notes/scripts/normalize_captions.py',str(root/'video.en-orig.json3'),str(root/'captions')],check=True)
cues = json.loads((root/'captions/captions.normalized.json').read_text())
groups = {}
for c in cues:
    groups.setdefault(c['start_ms']//60000,[]).append(c['text'])
assert ' '.join(' '.join(v) for v in groups.values()) == ' '.join(c['text'] for c in cues)
(root/'captions/reading-by-minute.txt').write_text('\n\n'.join(f'[{m:02d}:00]\n'+' '.join(v) for m,v in groups.items())+'\n')
for name in ['bitcoin','nielsen']:
    if not (root/(name+'.pdf')).exists():
        continue
    subprocess.run(['pdftotext','-layout',str(root/(name+'.pdf')),str(root/(name+'.layout.txt'))],check=True)
    doc = fitz.open(root/(name+'.pdf'))
    folder = root/(name+'-pages')
    folder.mkdir(exist_ok=True)
    for i,page in enumerate(doc):
        page.get_pixmap(matrix=fitz.Matrix(1.3,1.3)).save(folder/f'page-{i+1:02d}.png')
    print(name, len(doc), 'pages', doc.metadata)
print(len(cues),'cues',len(groups),'minute groups')
