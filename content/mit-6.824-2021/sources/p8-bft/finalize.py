"""Record completed human reading and run one bounded local content check."""
from pathlib import Path
import hashlib
import json
import re

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
COURSE = ROOT.parent
acquisition = json.loads((HERE / 'acquisition.json').read_text())
fields = ['url', 'final_url', 'file', 'sha256', 'retrieved_at', 'last_modified']
specs = [
    ('notes', 'Full text lines 1–342, including all ASCII traces and reference list. Internal title remains 6.5840 2024 Lecture 22; linked by 2026 L21. Lecture design stages are pedagogical simplifications, compared with paper definitions.',
     'MIT course-owned text, CC BY 3.0 US from home-2026.html line 61; attributed to MIT 6.5840 course team. No individually named author in this text.', [], [[1, 342]]),
    ('slides', 'Complete 23-page PDF, text and actual rendered pages 1–23. Internal Lecture 21; Derek Leung attribution from 2026 schedule. Includes assumptions, digital-signature notation, quorum formulas, recovery prompts, view rotation and optimization list. Page 17 contains only a recovery-example prompt; no board trace or video reconstructed.',
     'Independent full-translation/republication permission not established for guest slides. Derek Leung attributed from course schedule. Course-site CC is not automatically applied. Original commentary only, no page images published.', list(range(1, 24)), []),
    ('paper', 'Complete 14-page OSDI 1999 paper: abstract, sections 1–9, acknowledgments and all 37 bibliography entries. All actual pages 1–14 viewed, including Figures 1–2, Tables 1–3, message formats, predicates, bounds and implementation formulas. Cited technical proofs, MAC protocol report, dissertation and later systems not read.',
     'Miguel Castro and Barbara Liskov, Practical Byzantine Fault Tolerance, OSDI 1999. Full-translation permission not established; autonomous Chinese reading commentary, no original PDF pages published. Course-site CC not applied.', list(range(1, 15)), []),
]
sources = []
for original, (name, scope, license_text, pages, lines) in zip(acquisition['reused'], specs):
    entry = {key: original[key] for key in fields}
    entry.update(id=f'p8-bft-{name}', original_source_id=original['id'],
                 status='reviewed', scope=scope, license=license_text,
                 read_pages=pages, visual_pages=pages.copy(), read_lines=lines,
                 reused_snapshot=True)
    sources.append(entry)
entry = {key: acquisition['new'][key] for key in fields}
entry.update(id='p8-bft-faq', inventory_source_id='lec21-faq-4-2026',
             http_status=acquisition['new']['http_status'], status='reviewed',
             scope='Full text lines 1–206, all questions and answers. Corrected threshold wording at lines 84–93 using paper section 4.2; scoped FLP/one-third wording and lifetime fault bound. All external linked works remain unread.',
             license='MIT course-owned FAQ, CC BY 3.0 US from home-2026.html line 61; attributed to MIT 6.5840 course team. Does not cover linked papers.',
             read_pages=[], visual_pages=[], read_lines=[[1, 206]], reused_snapshot=False)
sources.append(entry)
manifest = {
    'topic': 'update-bft',
    'course_context': 'MIT 6.824 Spring 2021 main course; MIT 6.5840 Spring 2026 L21 (Derek Leung) written-material update',
    'sources': sources,
    'video_status': 'No video listed by the 2026 schedule; no draft, invented timestamps or classroom dialogue.',
    'artifacts': ['lectures/update-bft/notes.zh.md', 'lectures/update-bft/materials.zh.md'],
    'review': 'p8-bft/review.txt',
    'validation': 'p8-bft/validation.txt',
    'local_only': ['p8-bft/bft-faq.txt', 'p8-bft/acquisition.json', 'p8-bft/paper.txt',
                   'p8-bft/slides.txt', 'p8-bft/rendered/'],
    'execution': {'prototype': 'not_run', 'lab_tests': 'not_run', 'build': 'delegated_to_main_agent'},
}
assert len({x['id'] for x in sources}) == 4
for entry in sources:
    data = (ROOT / entry['file']).read_bytes()
    assert hashlib.sha256(data).hexdigest() == entry['sha256'], entry['file']
    if entry['read_lines']:
        assert len(data.decode().splitlines()) == entry['read_lines'][0][1]
    if entry['reused_snapshot']:
        original = next(x for x in acquisition['reused'] if x['id'] == entry['original_source_id'])
        for field in fields:
            assert entry[field] == original[field]
schedule = (ROOT / 'schedule-2026.html').read_text()
for source in sources:
    relative_url = source['url'].split('/6.824/')[1]
    assert f'href="{relative_url}"' in schedule
for artifact in manifest['artifacts']:
    text = (COURSE / artifact).read_text()
    assert text.startswith('---\n')
    header = text.split('---', 2)[1]
    assert {line.split(':', 1)[0] for line in header.strip().splitlines()} <= {'source', 'video', 'license', 'status'}
    assert text.count('<details>') == text.count('</details>')
    assert text.count('```') % 2 == 0
    assert not any(line.rstrip() != line for line in text.splitlines()), artifact
    for target, view in re.findall(r'#/c/mit-6\.824-2021/lec/([\w-]+)\?v=(notes|materials|draft)', text):
        assert (COURSE / 'lectures' / target / f'{view}.zh.md').is_file(), (target, view)
assert not (COURSE / 'lectures/update-bft/draft.zh.md').exists()
(HERE / 'manifest-fragment.json').write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + '\n')
result = ('PASS: four source hashes; three reused metadata records unchanged; exact text line counts; '
          'four actual schedule links; unique p8-bft source IDs; two Markdown headers, '
          'details/fences/trailing whitespace and lecture routes. No draft.\n'
          'Only source/content validation performed; no git, site build, PBFT implementation, '
          'formal proof or lab tests run.\n')
(HERE / 'validation.txt').write_text(result)
print(result)
