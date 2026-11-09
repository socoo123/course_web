"""Finalize L18 provenance and check local content only; no shared writes/build/git.

From repository root, run acquire.py, prepare-reading.py, then this script.
Requires yt-dlp and PyMuPDF for acquisition/preparation. Reacquisition may change
upstream bytes; frozen hashes below prevent carrying old semantic review forward.
"""
import hashlib
import json
import re
from datetime import datetime, timezone
from pathlib import Path

root=Path(__file__).parent
sources=root.parent
course=sources.parent
lecture=course/'lectures/lec18'
now=datetime.now(timezone.utc).isoformat()

def digest(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()

def millis(stamp):
    m,s=map(int,stamp.split(':'))
    return (m*60+s)*1000

frozen={
    'l-sundr.txt':'77e30b3bd196cbb1d7eb26e7958ed5d6e2a1468a2b34e1c200ea872435b0d2ab',
    'li-sundr.pdf':'b72c3e0b251a0a632fc823138a924e5cde76ff7dcba9b6eaf47480a675e1644d',
    'sundr-faq.txt':'63855613e568f1ac7d87104940c4b66f3df8e23ae4b90bd0ecfca9efef10a9e9',
    'metadata.json':'ce234c7a7f62a495c057b4c5fdac7f0dd169aa9624cf0f3124d4cb2bd24c2dfd',
    'video.en-orig.json3':'8480e645e9ba2a898b95c4cfd98a61f7c38cda2017d1be53c2ddbfce01b13d6f',
}
for name,expected in frozen.items():
    assert digest(root/name)==expected, 'Changed source requires new semantic review: '+name
meta=json.loads((root/'metadata.json').read_text())
assert set(meta)=={'id','title','duration','channel','channel_id','uploader','upload_date','license','webpage_url'}
assert meta['id']=='FxwjSs_xSBM' and meta['duration']==5464
assert meta['title']=='Lecture 18: Fork Consistency, SUNDR' and meta['upload_date']=='20210506'
cues=json.loads((root/'captions/captions.normalized.json').read_text())
assert len(cues)==2149
assert all(0<=c['start_ms']<=c['end_ms'] for c in cues)
assert all(a['start_ms']<=b['start_ms'] for a,b in zip(cues,cues[1:]))
raw=[]
for e in json.loads((root/'video.en-orig.json3').read_text())['events']:
    text=''.join(s.get('utf8','') for s in e.get('segs',[])).strip()
    if text:
        raw.append(dict(start_ms=e['tStartMs'],end_ms=e['tStartMs']+e.get('dDurationMs',0),text=text))
assert raw==cues
grouped=' '.join(line for line in (root/'captions/reading-by-minute.txt').read_text().splitlines()
                 if line and not re.fullmatch(r'\[\d+:00\]',line))
assert grouped==' '.join(c['text'] for c in cues)

draft=(lecture/'draft.zh.md').read_text()
segments=[dict(start=a,end=b,start_ms=millis(a),end_ms=millis(b),title=t)
          for a,b,t in re.findall(r'^## (\d+:\d{2})–(\d+:\d{2}) (.+)$',draft,re.M)]
duration=meta['duration']*1000
assert len(segments)==35 and segments[0]['start_ms']==0 and segments[-1]['end_ms']==duration
assert all(s['start_ms']<s['end_ms'] for s in segments)
assert all(a['end_ms']==b['start_ms'] for a,b in zip(segments,segments[1:]))
for c in cues:
    assert sum(s['start_ms']<=c['start_ms']<s['end_ms'] for s in segments)==1
for s in segments:
    found=[i+1 for i,c in enumerate(cues) if s['start_ms']<=c['start_ms']<s['end_ms']]
    s.update(cue_count=len(found),first_cue=found[0] if found else None,last_cue=found[-1] if found else None)
end=0
covered=0
gaps=[]
for c in cues:
    if c['start_ms']>end:
        gaps.append(dict(start_ms=end,end_ms=c['start_ms'],duration_ms=c['start_ms']-end))
    covered+=max(0,min(c['end_ms'],duration)-max(end,c['start_ms']))
    end=max(end,c['end_ms'])
if end<duration:
    gaps.append(dict(start_ms=end,end_ms=duration,duration_ms=duration-end))
stats=dict(cue_count=len(cues),first_start_ms=cues[0]['start_ms'],last_start_ms=cues[-1]['start_ms'],
    last_end_ms=end,metadata_duration_seconds=meta['duration'],starts_monotonic=True,negative_duration_count=0,
    ends_monotonic=all(a['end_ms']<=b['end_ms'] for a,b in zip(cues,cues[1:])),
    overlapping_adjacent_cue_pairs=sum(a['end_ms']>b['start_ms'] for a,b in zip(cues,cues[1:])),
    cues_ending_after_video=sum(c['end_ms']>duration for c in cues),tail_overrun_ms=max(0,end-duration),
    tail_uncaptioned_ms=max(0,duration-end),positive_uncovered_gap_count=len(gaps),
    uncovered_ms_within_video=duration-covered,maximum_uncovered_gap_ms=max(g['duration_ms'] for g in gaps),
    all_uncovered_gaps=gaps,draft_segment_count=len(segments),draft_start='00:00',draft_end='91:04',
    audio_reviewed=False,video_frames_reviewed=False,
    interpretation='All ASR texts read in order. Interval-union gaps are not silence detection. Zoom failures 30:22–33:20 (screen recovery continues through 34min), 61:42–63:22; breakout 43:14–49:18 unrecoverable. Original 1920ms tail overrun retained.')
assert stats['positive_uncovered_gap_count']==153
assert stats['uncovered_ms_within_video']==686690
assert stats['maximum_uncovered_gap_ms']==182720 and stats['tail_overrun_ms']==1920

paper_scope={
    'assigned_scope_original_2021':'until Section 3.4',
    'assigned_scope_original_2026':'through the end of Section 3.3.2',
    'boundary':'Stop immediately before Section 3.4, after Section 3.3.2 including Figure 5 and its final continuation on PDF p6. 2021 until is interpreted as exclusive; original wording preserved.',
    'boundary_evidence':'2021 schedule lines 241–242; 2026 schedule lines 249–250; paper p3 three-stage roadmap and p4 description of serialized/concurrent split; 2021 outline lines 229–233 leave full update certificates to paper.',
    'assigned_reading_complete':True,
    'read_sections':['Abstract','1','2','3 introduction','3.1','3.2','3.3 introduction','3.3.1','3.3.2'],
    'read_pages':'PDF 1–5 and p6 before Section 3.4; original 16-page PDF not fully read.',
    'additional_targeted_reading':'Full extracted p6–7 also read to verify concurrency boundary: Section 3.4 introduction, 3.4.1, and p7 portion of 3.4.2. This is supplemental partial reading, not a complete Section 3.4 review.',
    'unread':'PDF 8–16; remainder of concurrency, implementation/evaluation/references and external formal proofs. No full-paper or full-evaluation claim.',
    'figures_reviewed':[1,2,3,4,5],
    'tables_reviewed':[],
    'visual_pages':[2,3,4,5,6,7],
}
scopes={
    'l-sundr.txt':'All 239 lines read; correct internal title 6.824 2021 Lecture 18. Full comparison to existing 306-line 2026 outline. Residual last lecture on messaging does not match actual preceding Memcached lecture. Concurrent update certificates mentioned but not fully taught in available video.',
    'sundr-faq.txt':'All 54 lines / five questions read: confidentiality, i-handle computation and change log, out-of-band detection/timestamp box, historical applications/Keybase, compromised trusted servers. External incident links and current product internals not independently read/verified.',
    'li-sundr.pdf':paper_scope,
    'metadata.json':'Independently queried all whitelist fields; title Lecture 18: Fork Consistency, SUNDR; channel MIT 6.824: Distributed Systems / UC_7WrbZTCODu1o_kfUMq88g; upload 20210506; duration 5464 seconds / 91:04; Creative Commons Attribution license (reuse allowed), version unspecified.',
    'video.en-orig.json3':'All 2149 original-language English automatic caption texts read in sequential lossless minute groups, reading-by-minute.txt lines 1–145 then 146–266. Raw cues additionally inspected at 30:00–34:10,42:50–50:05,60:50–64:20,87:30–89:10,90:30–end. No audio/frame review. 35 segments preserve questions, demonstrations described in speech, two Zoom failures and breakout gap. ASR terminology and negations explicitly annotated.',
}
entries=json.loads((root/'acquisition.json').read_text())
for e in entries:
    name=Path(e['file']).name
    assert digest(sources/e['file'])==e['sha256']
    e.update(status='partial' if name=='li-sundr.pdf' else 'reviewed',reviewed_at=now,scope=scopes[name])
    if name in ['l-sundr.txt','sundr-faq.txt']:
        e['license']=dict(label='CC BY 3.0 US',evidence_file='home-2021.html',evidence_scope='Line 55 checked; 2021 course-authored text only.',url='https://creativecommons.org/licenses/by/3.0/us/')
    elif name=='li-sundr.pdf':
        e['license']='Full translation permission unconfirmed; original analytical Chinese reading only.'
    else:
        e.update(license=meta['license'],license_note='Video-specific query; version absent; not inherited from website.',
                 last_modified_note='Not exposed in whitelist/caption acquisition; unknown.',
                 final_url_note='Signed subtitle transport URLs deliberately not persisted.')
    if name=='video.en-orig.json3':
        e.update(language='en-orig',caption_type='original-language English automatic ASR')

legacy=json.loads((sources/'manifest.json').read_text())['sources']
for filename,label,scope,status in [
    ('update-2026-l-sundr.txt','outline','All 306 lines read, together with all 239 lines of 2021 outline and full 543-line diff. New hash/signature/content-addressed-storage tutorial, x.c/NEWS example, three-user vectors and explicit failed-splice cases; 2021 timestamp/ownership/concurrency detail not all retained. No new protocol revision.','reviewed'),
    ('update-2026-li-sundr.pdf','paper',paper_scope,'partial')]:
    old=next(e for e in legacy if e.get('file')==filename)
    assert digest(sources/filename)==old['sha256']
    entry={k:old.get(k) for k in ['url','final_url','retrieved_at','last_modified','file','sha256']}
    entry.update(id='lec18-p7-comparison-2026-'+label,upstream_manifest_id=old['id'],
        status=status,reviewed_at=now,scope=scope,
        acquisition_note='Existing 2026-11-08 read-only snapshot reused, not refetched. PDF byte-identical to newly fetched 2021 PDF; same reading/visual pass applies, not a second independent pass.',
        license='2026 outline license not independently verified; paper full-translation permission unconfirmed. Analytical comparison only.')
    entries.append(entry)
assert (root/'li-sundr.pdf').read_bytes()==(sources/'update-2026-li-sundr.pdf').read_bytes()

derived=[]
def add_derived(name,parent,status,scope):
    p=root/name
    derived.append(dict(id='lec18-p7-derived-'+name.replace('/','-'),file='p7-lec18/'+name,
        sha256=digest(p),status=status,scope=scope,derived_from=parent,derived_at=now))

add_derived('captions/captions.normalized.json','p7-lec18/video.en-orig.json3','reviewed',
            'All cue texts read through lossless grouping; specified raw intervals reread for times/ASR; full structure checked.')
add_derived('captions/reading-by-minute.txt','p7-lec18/video.en-orig.json3','reviewed',
            'All 266 lines sequentially read, 89 nonempty minute groups; concatenated text equality checked.')
add_derived('captions/transcript.en.txt','p7-lec18/video.en-orig.json3','fetched',
            'Generated timed representation only; same full text read in minute grouping, not independently reread here.')
add_derived('lecture-2021-2026.diff.txt',['p7-lec18/l-sundr.txt','update-2026-l-sundr.txt'],'reviewed',
            'All 543 diff lines read after both complete outlines.')
visual={2:'Figure 1, interface layers, footnotes 1 and 2; public-key and last-operation prerequisites.',
        3:'Both unnumbered operation-log diagrams, normal and forked prefixes; honest/compromised user distinction.',
        4:'Section 3.3 boundary, content-addressed structure definitions, user/group mapping.',
        5:'Figures 2 and 3; group indirection, directory paths, version-structure fields and z construction equations.',
        6:'Figures 4 and 5; actual vector values (3,1)/(2,2), partial-order/all-entry-plus-z checks, change log; exact 3.4 boundary. Supplemental 3.4/3.4.1 text and formulas also inspected.',
        7:'Supplemental partial concurrency review: PVL equations and ordering, read-after-write waiting and group write conflict evidence. Not a full Section 3.4 review.'}
for page in range(1,8):
    add_derived(f'paper-page-{page:02d}.txt','p7-lec18/li-sundr.pdf','reviewed',
                'All extracted page text read. '+('Assigned reading.' if page<6 else 'Assigned part and/or supplemental boundary reading; see source scope.'))
    add_derived(f'paper-pages/page-{page:02d}.png','p7-lec18/li-sundr.pdf',
                'reviewed' if page in visual else 'fetched',
                visual.get(page,'Rendered only; p1 full text read, image not separately inspected.'))

documents=[]
for p in sorted(lecture.glob('*.zh.md')):
    text=p.read_text()
    assert text.startswith('---\n') and '\nstatus:' in text
    assert text.count('```')%2==0 and text.count('<details>')==text.count('</details>')
    assert all(line.rstrip()==line for line in text.splitlines())
    for ident,view in re.findall(r'#/c/mit-6\.824-2021/lec/([^?\s)]+)\?v=(\w+)',text):
        assert (course/'lectures'/ident/(view+'.zh.md')).is_file(),(ident,view)
    for image in re.findall(r'!\[[^]]*\]\(([^)]+)\)',text):
        assert (p.parent/image).is_file()
    documents.append(dict(file=str(p.relative_to(course)),sha256=digest(p),status='completed'))
assert len(documents)==3
assert len({e['id'] for e in entries+derived})==len(entries+derived)

video=dict(video_id=meta['id'],url=meta['webpage_url'],metadata=meta,metadata_file='p7-lec18/metadata.json',
    normalized_caption_file='p7-lec18/captions/captions.normalized.json',raw_caption_file='p7-lec18/video.en-orig.json3',
    caption_time_structure=stats,draft_segment_count=len(segments),draft_segments=segments,
    review_status='reviewed_text_not_audio_or_frames')
fragment=dict(course_id='mit-6.824-2021',lecture_id='lec18',batch='P7',
    content_status='completed_for_assigned_reading_and_available_classroom_text_with_explicit_gaps',
    review_file='p7-lec18/review.txt',acquisition_file='p7-lec18/acquisition.json',
    sources=entries,derived_files=derived,videos=[video],caption_time_structure=stats,draft_segments=segments,
    paper_reading_scope=paper_scope,paper_visual_review=dict(pdf_pages=16,figures=[1,2,3,4,5],tables=[],inspected_page_images=sorted(visual)),
    version_mapping_evidence=dict(file='schedule-2021.html',scope='Lines 240–242: 2021-05-06, L18, l-sundr.txt, FxwjSs_xSBM, li-sundr.pdf until Section 3.4, sundr-faq.txt. Inventory lec18 independently checked.'),
    version_comparison=dict(papers_identical_bytes=True,paper_sha256=frozen['li-sundr.pdf'],
        outline_diff='p7-lec18/lecture-2021-2026.diff.txt',new_update_created=False,
        old_internal_title='6.824 2021 Lecture 18',new_internal_title='6.5840 2026 Lecture 19',
        differences=['Explicit content-hash storage / signed mutable handle tutorial','x.c/NEWS replaces Zoobar example',
                     'Three-user vector table and explicit failed-splice cases','2021 timestamp box, ownership and concurrency details not fully repeated in 2026']),
    documents=documents,content_paths=[d['file'] for d in documents],
    validation=dict(source_hashes='passed',lossless_caption_grouping='passed',caption_time_structure='passed_with_raw_overrun',
        draft_timeline='passed',local_markdown_routes_images_structure='passed',audio_visual_review='not performed',
        build='Not run by restricted worker; main agent integrates.',experiments='not_run',
        lab_code_commit='513cac0aef010750fc74688da8a395974a83cf7a',no_media_download=True,
        no_full_player_response_saved=True,no_cookies_saved=True,no_signed_urls_saved=True),
    issues=['Two Zoom interruptions and unrecoverable breakout text; all 153 interval gaps are not audio silence claims.',
            'Last cue ends at 91:05.920, 1920ms past integer duration; source untrimmed.',
            'ASR private/public signing, not-only phrase, 88min can/cannot merge, Zoobar/Frangipani names and ambiguous block size annotated without audio claims.',
            'Paper 16 pages only assigned prefix fully read; supplemental p6–7 does not complete Concurrent SUNDR. PDF 8–16 unread.',
            '2021 until Section 3.4 kept verbatim and interpreted exclusive based on paper/outline; 2026 through end 3.3.2 separately preserved.',
            'Video CC version, paper full-translation rights and 2026 outline licensing unconfirmed; original paraphrase/analysis only.',
            'SHA-1 is historical protocol choice; generic collision-resistance assumptions are not a current SHA-1 security recommendation.',
            'No automatic fork healing, global freshness, arbitrary multi-file snapshot transaction, confidentiality or availability claim.',
            'Historical incident/product assertions not extended to current deployments; Debian confirmed intrusion/assessment distinguished from proven infected distributions.',
            '2026 FAQ remains not acquired; no external proofs, full implementation/evaluation or lab tests read/run.'])
(root/'manifest-fragment.json').write_text(json.dumps(fragment,ensure_ascii=False,indent=2)+'\n')
summary={k:v for k,v in stats.items() if k!='all_uncovered_gaps'}
(root/'validation.txt').write_text(json.dumps(summary,ensure_ascii=False,indent=2)+'\nSource hashes, lossless cues, continuous 35-segment draft and local Markdown routes/structure passed. No build, shared edits or experiment tests.\n')
print(json.dumps(summary,ensure_ascii=False,indent=2))
