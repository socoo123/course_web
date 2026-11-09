"""Check only assigned sources/content; distinguish full text reading from visual spots."""
import hashlib
import json
import re
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).parent
SOURCES = ROOT.parent
COURSE = SOURCES.parent
LECTURE = COURSE/'lectures/lec20'
NOW = datetime.now(timezone.utc).isoformat()

def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

def ms(stamp):
    m, s = map(int, stamp.split(':'))
    return (60*m+s)*1000

meta = json.loads((ROOT/'metadata.json').read_text())
assert meta['id'] == 'DnyBPxo3B6I' and meta['duration'] == 5383
assert set(meta) == {'id','title','duration','channel','channel_id','uploader','upload_date','license','webpage_url'}
cues = json.loads((ROOT/'captions/captions.normalized.json').read_text())
assert len(cues) == 2363
duration = meta['duration']*1000
draft = (LECTURE/'draft.zh.md').read_text()
segments = [dict(start=a,end=b,start_ms=ms(a),end_ms=ms(b),title=t)
            for a,b,t in re.findall(r'^## (\d+:\d{2})–(\d+:\d{2}) (.+)$',draft,re.M)]
assert segments[0]['start_ms'] == 0 and segments[-1]['end_ms'] == duration
assert all(a['end_ms'] == b['start_ms'] for a,b in zip(segments,segments[1:]))
assert all(s['end_ms'] > s['start_ms'] for s in segments)
assert all(a['start_ms'] <= b['start_ms'] for a,b in zip(cues,cues[1:]))
assert all(c['end_ms'] >= c['start_ms'] >= 0 for c in cues)
assert all(sum(s['start_ms'] <= c['start_ms'] < s['end_ms'] for s in segments) == 1 for c in cues)
for s in segments:
    selected = [(i+1,c) for i,c in enumerate(cues) if s['start_ms'] <= c['start_ms'] < s['end_ms']]
    s.update(cue_count=len(selected),first_cue=selected[0][0] if selected else None,
             last_cue=selected[-1][0] if selected else None)
grouped = (ROOT/'captions/reading-by-minute.txt').read_text()
grouped_text = ' '.join(line for line in grouped.splitlines() if line and not re.fullmatch(r'\[\d+:00\]',line))
assert grouped_text == ' '.join(c['text'] for c in cues)
gaps = []
end = covered = 0
for c in cues:
    if c['start_ms'] > end:
        gaps.append(dict(start_ms=end,end_ms=c['start_ms'],duration_ms=c['start_ms']-end))
    covered += max(0,min(c['end_ms'],duration)-max(end,c['start_ms']))
    end = max(end,c['end_ms'])
if end < duration:
    gaps.append(dict(start_ms=end,end_ms=duration,duration_ms=duration-end))
stats = dict(cue_count=len(cues),first_start_ms=cues[0]['start_ms'],last_start_ms=cues[-1]['start_ms'],
    last_end_ms=cues[-1]['end_ms'],metadata_duration_seconds=meta['duration'],starts_monotonic=True,
    ends_monotonic=all(a['end_ms'] <= b['end_ms'] for a,b in zip(cues,cues[1:])),
    negative_duration_count=sum(c['end_ms'] < c['start_ms'] for c in cues),
    cues_ending_after_video=sum(c['end_ms'] > duration for c in cues),
    tail_overrun_ms=max(0,end-duration),tail_uncaptioned_ms=max(0,duration-end),
    overlapping_adjacent_cue_pairs=sum(a['end_ms'] > b['start_ms'] for a,b in zip(cues,cues[1:])),
    positive_uncovered_gap_count=len(gaps),uncovered_ms_within_video=duration-covered,
    maximum_uncovered_gap_ms=max(g['duration_ms'] for g in gaps),all_uncovered_gaps=gaps,
    draft_segment_count=len(segments),draft_start=segments[0]['start'],draft_end=segments[-1]['end'],
    audio_reviewed=False,video_frames_reviewed=False,
    interpretation='Interval-union gaps only, not silence detection. All2363 cue texts read sequentially using lossless minute grouping. Lecturer explicitly replaces breakout rooms with whole-class discussion around66-67min. 48:48.880-49:00.960 loses start of zone-file availability answer. Raw1880ms tail overrun retained.')
assert len(gaps) == 160 and duration-covered == 413118 and end-duration == 1880

scopes = {
    'l-blockstack.txt': 'All330 lines read. Explicit 6.8242021 Lecture20 Blockstack(2016) heading. Entire app/naming/storage/key management/discussion outline and two external reference entries read; external documents/code not read. Atlas/Gaia/Browser vocabulary is outline-specific, not backfilled into2016 paper. Last-Modified2021-05-18 19:06:55GMT may be later than class preparation.',
    'blockstack-faq.txt': 'All174 lines read, including CT, pricing, privacy, identity/recovery, SQL/groups/auctions/shared aggregates and Consistency Hashes. Heading has no year; opening refers to whitepaper and links2016 paper plus May2019 whitepaper despite2021 schedule assigning2016 PDF. Those external documents were not fetched. Last-Modified2021-01-22 09:21:42GMT.',
    'blockstack-atc16.pdf': 'All15 PDF pages read via complete846-line layout extraction: cover, abstract, sections1-7, acknowledgements and53 bibliography entries; printed pages181-194. All8 figures and both SNV formulas checked on actual page images; no numbered tables. Cover and pages5,6,7,8,10,11,12 visually inspected. Other page text read in extraction, not separately image-reviewed. No bibliography-linked full texts read. Internal title Blockstack: A Global Naming and Storage System Secured by Blockchains, USENIX ATC2016; Last-Modified2021-01-22 is server snapshot date.',
    'metadata.json': 'Independent whitelist query: DnyBPxo3B6I; Lecture20: Blockstack;5383seconds/89:43; MIT6.824: Distributed Systems; UC_7WrbZTCODu1o_kfUMq88g; uploaded20210518; Creative Commons Attribution license(reuse allowed), exact version unspecified.',
    'video.en-orig.json3': 'All2363 original-language English ASR cue texts sequentially read through90 lossless minute groups/269lines in ranges1-100,101-200,201-269; includes public discussion and post-class questions. Normalized cues48:20-49:10 directly inspected after full read. No breakout session: lecturer explicitly chooses discussion. First80ms, last start5379440ms, end5384880ms,1880ms over integer duration. No audio/classroom-frame review; all available content organized into'+str(len(segments))+' consecutive draft segments.'
}
entries = json.loads((ROOT/'acquisition.json').read_text())
for entry in entries:
    name = Path(entry['file']).name
    assert digest(SOURCES/entry['file']) == entry['sha256']
    entry.update(status='reviewed',reviewed_at=NOW,scope=scopes[name])
    if name in ('l-blockstack.txt','blockstack-faq.txt'):
        entry['license'] = dict(label='CC BY3.0US',evidence_file='home-2021.html',evidence_line=55,
            url='https://creativecommons.org/licenses/by/3.0/us/',scope='Course-authored text only; no extension to paper/video.')
    elif name.endswith('.pdf'):
        entry['license'] = 'Full translation permission unconfirmed; original Chinese analytical reading, no public reproduction of page images.'
    else:
        entry['license'] = meta['license']
        entry['license_note'] = 'Independent video metadata; exact CC version absent.'
    if name == 'video.en-orig.json3':
        entry.update(language='en-orig',caption_type='original-language automatic English ASR')

derived = []
def add_derived(rel,status,scope,parent):
    p = ROOT/rel
    derived.append(dict(id='lec20-2021-derived-'+rel.replace('/','-'),file='p7-lec20/'+rel,
        sha256=digest(p),status=status,scope=scope,derived_from='p7-lec20/'+parent,
        generated_at=datetime.fromtimestamp(p.stat().st_mtime,timezone.utc).isoformat()))

for rel,status,scope in [
    ('captions/captions.normalized.json','reviewed','All cue text read through lossless grouping;48:20-49:10 normalized cue objects directly checked; time structure programmatically checked.'),
    ('captions/reading-by-minute.txt','reviewed','All269 lines/90 groups read sequentially; concatenation equals all2363 cues, not a filtered summary.'),
    ('captions/transcript.en.txt','reviewed','Same complete cue text read in grouping representation; this output not independently reread.'),
    ('captions/captions.en.vtt','fetched','Generated only; not played or independently line-read.')]:
    add_derived(rel,status,scope,'video.en-orig.json3')
add_derived('blockstack-atc16.layout.txt','reviewed','All846lines read sequentially in ranges1-380,381-760,761-846; dual-column continuations followed; cover, abstract, all sections and references included.','blockstack-atc16.pdf')
visual = {
    1:'Actual cover: exact internal title, four authors, USENIX ATC2016 publication and open-access wording (not translation license).',
    5:'Figure1 weekly/daily mining power percentages, Slush/F2Pool; security and51% qualifications.',
    6:'Figure2(a) log1-CDF and50/90/99/99.9percentiles7/22/46/78min;(b) latency vs block height; selfish-mining-like caveat.',
    7:'Figure3 separate block-confirmation time and accepted transactions/target; merged-mining denominator.',
    8:'Figure4 all four layers, virtualchain processor, name histories and mutable/immutable paths.',
    10:'Figure5 absent/preordered/registered/revoked, PREORDER/REGISTER/EXPIRE/UPDATE/TRANSFER/RENEW/REVOKE; both storage modes text.',
    11:'Figure6 geometric SNV verification; both CH(h),P_h equations; trusted hash precondition; Simple vs Simplified title/body discrepancy.',
    12:'Figures7-8: milliseconds and per-file components, excluded download,100MB performance vs prose2s claim; logarithmic transaction counts and three populations; migration and26.9percent denominator.'
}
for p in sorted((ROOT/'paper-pages').glob('page-*.png')):
    page = int(p.stem.split('-')[1])
    add_derived(str(p.relative_to(ROOT)),'reviewed' if page in visual else 'fetched',
        visual.get(page,'Rendered only; full page text read in layout extraction, image not independently inspected.'),'blockstack-atc16.pdf')

assert {p.name for p in LECTURE.glob('*.md')} == {'draft.zh.md','notes.zh.md','materials.zh.md'}
course_ids = {x['id'] for x in json.loads((COURSE/'course.json').read_text())['lectures']}
for p in LECTURE.glob('*.md'):
    text = p.read_text()
    assert text.startswith('---\n') and '\nstatus:' in text
    assert len(re.findall(r'^```',text,re.M)) % 2 == 0
    assert all(line.rstrip() == line for line in text.splitlines())
    for other,view in re.findall(r'#/c/mit-6\.824-2021/lec/([^?\s)]+)\?v=(\w+)',text):
        assert other in course_ids and (COURSE/'lectures'/other).is_dir(), (other,view)
    for image in re.findall(r'!\[[^]]*\]\(([^)]+)\)',text):
        assert (p.parent/image).is_file()
assert not any(ROOT.rglob('*.md'))

video = dict(video_id=meta['id'],url=meta['webpage_url'],metadata=meta,
    metadata_file='p7-lec20/metadata.json',normalized_caption_file='p7-lec20/captions/captions.normalized.json',
    caption_time_structure=stats,draft_segment_count=len(segments),draft_segments=segments)
fragment = dict(course_id='mit-6.824-2021',lecture_id='lec20',batch='P7',
    content_status='completed_for_available_text_with_explicit_asr_gaps_and_audio_visual_limits',
    review_file='p7-lec20/review.txt',acquisition_file='p7-lec20/acquisition.json',
    sources=entries,derived_files=derived,videos=[video],caption_time_structure=stats,draft_segments=segments,
    paper_visual_review=dict(pdf_pages=15,printed_pages='181-194;PDFpage1 cover',figures=list(range(1,9)),
        tables=[],formula_pages=[11],inspected_page_images=sorted(visual),audio_or_classroom_frames=False),
    version_mapping_evidence=dict(file='schedule-2021.html',lines=[261,262],
        scope='2021-05-18 L20 matches inventory; exact2016 PDF, outline, FAQ and DnyBPxo3B6I links; all shared files read-only.'),
    content_paths=[str(p.relative_to(COURSE)) for p in sorted(LECTURE.glob('*.md'))],
    content_files=[dict(file=str(p.relative_to(COURSE)),sha256=digest(p)) for p in sorted(LECTURE.glob('*.md'))],
    lab_code_commit='513cac0aef010750fc74688da8a395974a83cf7a',
    validation=dict(source_hashes='passed',lossless_grouping='passed',caption_structure='passed_with_retained_raw_tail_overrun',
        continuous_draft_timeline='passed',markdown_local_structure='passed',
        build='Not run by restricted worker; integrated check belongs to main agent.',experiments='Not run',
        no_media_download=True,no_full_player_response_saved=True,no_signed_urls_saved=True),
    issues=[
        'No audio or classroom-frame review.160 positive caption union gaps413118ms total,max22240ms; not silence detection. Raw1880ms tail overrun retained.',
        'No breakout: lecturer explicitly substitutes whole-class discussion.48:48.880-49:00.960 lacks start of availability answer; not reconstructed as speech.',
        'Video CC Attribution exact version absent; paper full-translation permission unconfirmed.',
        '2016 PDF is15pages with cover, not modern Stacks or2019 whitepaper.2021 outline uses Atlas/Gaia/Browser beyond2016 DHT/storage terminology; FAQ opening refers to whitepaper.',
        'Lecture date vs outline Last-Modified same day does not prove pre-class snapshot. PDF/FAQ server date2021 is not publication date.',
        'Name ownership, real-world identity, consensus ordering, integrity, freshness, availability and privacy explicitly separated.',
        'Mutable version numbers do not prove latest state; immutable data freshness assumes current authentic naming state. No global transaction guarantee for chain-off mutable files.',
        'Signing uses private key, not public key; public-key wording in ASR/paper corrected.51percent hash power does not forge signatures.',
        'Preorder/register is commit-reveal, not transaction2PC; bare hash(name) dictionary issue and unspecified commitment encoding preserved.',
        'SNV trusted starting consensus hash is a precondition; logarithmic proof queries not logarithmic complete-state reconstruction. Simple/Simplified naming discrepancy retained.',
        'Figure7 excludes read download time;100MB encryption/read components do not support blanket2-second overhead claim.26.9percent inFigure8 concerns data-embedding transactions, not allBitcoin.',
        'Namecoin selfish-mining-like observations do not prove malicious intent;2016 security/market/deployment claims not modern status.',
        'Keybase/global-name classroom analogy not treated as verified product specification; Kerberos PKI usage qualified; nonce, URI schema and access-control implementation not invented.',
        'End-of-class checkpoint/pruning suggestions are not a verified Bitcoin full-node protocol; headers alone insufficient for arbitrary state validation.',
        'No external references, source code, modern product behavior or lab executions claimed; fixed2026 commit retained.'
    ])
(ROOT/'manifest-fragment.json').write_text(json.dumps(fragment,ensure_ascii=False,indent=2)+'\n')
summary = {k:v for k,v in stats.items() if k != 'all_uncovered_gaps'}
(ROOT/'validation.txt').write_text(json.dumps(summary,ensure_ascii=False,indent=2)+'\nPASS local sources, whitelist, grouping, timeline, routes and Markdown. No build/media review/lab tests.\n')
print(json.dumps(summary,ensure_ascii=False,indent=2))
