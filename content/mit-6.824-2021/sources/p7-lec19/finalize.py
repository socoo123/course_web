"""Local provenance/timeline/route verification; no shared writes, build or lab execution."""
import hashlib
import json
import re
from datetime import datetime, timezone
from pathlib import Path

root = Path(__file__).parent
sources = root.parent
course = sources.parent
lecture = course/'lectures/lec19'
now = datetime.now(timezone.utc).isoformat()

def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

def ms(stamp):
    m,s = map(int,stamp.split(':'))
    return (60*m+s)*1000

meta = json.loads((root/'metadata.json').read_text())
assert meta['id'] == 'yB6m8EjAqPU' and meta['duration'] == 4964
assert meta['title'] == 'Lecture 19: Peer-to-Peeer: Bitcoin'
assert meta['channel'] == 'MIT 6.824: Distributed Systems' and meta['upload_date'] == '20210511'
assert set(meta) == {'id','title','duration','channel','channel_id','uploader','upload_date','license','webpage_url'}
cues = json.loads((root/'captions/captions.normalized.json').read_text())
assert len(cues) == 2163
assert all(a['start_ms'] <= b['start_ms'] for a,b in zip(cues,cues[1:]))
assert all(c['end_ms'] >= c['start_ms'] >= 0 for c in cues)
duration = meta['duration']*1000
draft = (lecture/'draft.zh.md').read_text()
segments = [dict(start=a,end=b,start_ms=ms(a),end_ms=ms(b),title=t)
    for a,b,t in re.findall(r'^## (\d+:\d{2})–(\d+:\d{2}) (.+)$',draft,re.M)]
assert segments[0]['start_ms'] == 0 and segments[-1]['end_ms'] == duration
assert all(s['start_ms'] < s['end_ms'] for s in segments)
assert all(a['end_ms'] == b['start_ms'] for a,b in zip(segments,segments[1:]))
assert all(sum(s['start_ms'] <= c['start_ms'] < s['end_ms'] for s in segments) == 1 for c in cues)
for s in segments:
    selected = [(i+1,c) for i,c in enumerate(cues) if s['start_ms'] <= c['start_ms'] < s['end_ms']]
    s.update(cue_count=len(selected),first_cue=selected[0][0] if selected else None,
             last_cue=selected[-1][0] if selected else None)
grouped = (root/'captions/reading-by-minute.txt').read_text()
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
    last_end_ms=end,metadata_duration_seconds=meta['duration'],starts_monotonic=True,
    ends_monotonic=all(a['end_ms'] <= b['end_ms'] for a,b in zip(cues,cues[1:])),negative_duration_count=0,
    cues_ending_after_video=sum(c['end_ms'] > duration for c in cues),tail_overrun_ms=max(0,end-duration),
    tail_uncaptioned_ms=max(0,duration-end),overlapping_adjacent_cue_pairs=sum(a['end_ms'] > b['start_ms'] for a,b in zip(cues,cues[1:])),
    positive_uncovered_gap_count=len(gaps),uncovered_ms_within_video=duration-covered,
    maximum_uncovered_gap_ms=max(g['duration_ms'] for g in gaps),all_uncovered_gaps=gaps,
    draft_segment_count=len(segments),draft_start=segments[0]['start'],draft_end=segments[-1]['end'],
    audio_reviewed=False,video_frames_reviewed=False,
    interpretation='All2163 cue texts sequentially read through lossless83-minute grouping. No breakout announced. Program crash near74:44 and largest11s caption-union gap74:57.840–75:08.840 retained. Union gaps are not silence detection. Raw tail1520ms over integer video duration retained.')
assert len(gaps) == 136 and duration-covered == 292866 and stats['tail_overrun_ms'] == 1520

scopes = {
    'l-bitcoin.txt':'All286 lines read: full2021L19 outline, transactions, all double-spend/fork scenarios, mining, validation, selfish-mining prompt, all questions and reference entries. External SoK/Script/OReilly texts not read. Internal title6.8242021Lecture19; Last-Modified2021-05-11 matches date but not proof of unchanged class-time content.',
    'bitcoin-faq.txt':'All340 lines/all Q&A read. Includes key theft, rewards, timestamp/propagation rationale, full chain vs headers, pools, fees, quantum speculation, monetary/price questions. No year in heading; same Last-Modified as outline but retains12.5BTC and60+GB stale examples. Linked modern sites, studies and current implementations not read.',
    'bitcoin.pdf':'All9 PDF pages,485 layout lines, abstract, sections1–12 and8 bibliography entries read; external cited works not read. Actual page images2–8 checked: all7 diagram groups, header-storage equation, all probability formulas, C implementation and3 numerical lists. Internal titleBitcoin:A Peer-to-Peer Electronic Cash System; assigned2008, PDF creation2009-03-24, server Last-Modified2021-01-22 distinguished.',
    'nielsen.pdf':'Full Bitcoin essay in ten-page third-party UBC/fivefilters PDF read by per-page columns, all736 extracted layout lines inspected. Assigned essay begins p1 lower-left, continues full p2–9, ends p10 left and right-column footnote. Includes all3 Problems for the author, conclusion and footnote; no comments included or read. All10 actual pages inspected, all6 figures and image-based formulas checked; a few standalone variable images are blank in PDF itself, not reconstructed as verified original. Adjacent unrelated announcements not counted as Bitcoin scope. PDF titlePDF Newspaper; first page starts How the backpropagation algorithm works, not actual article title; Bitcoin article byMichaelNielsen2013-12-06. UBC Last-Modified2015-03-27 and PDF creation2015-03-27 are snapshot dates. Original website404 after3 initial variants plus1 explicit retry; cannot establish last original-page revision or comments completeness.',
    'metadata.json':'Independently acquired9 whitelisted fields checked. yB6m8EjAqPU; original titleLecture19:Peer-to-Peeer:Bitcoin retains typo;4964seconds82:44;MIT6.824:DistributedSystems;UC_7WrbZTCODu1o_kfUMq88g;upload20210511;CreativeCommonsAttribution label exact version absent.',
    'video.en-orig.json3':'All2163 original-language automatic English cue texts read sequentially via lossless reading-by-minute lines1–125 then126–248,83 minute groups. Targeted normalized-cue reinspection08:00–09:00 SHA-1,69:00–70:00 throughput,74:00–76:00 crash,81:00–end compaction. Entire available lecture/post-class Q&A organized in'+str(len(segments))+' continuous editorial segments. First3520ms; last start4957040ms/end4965520ms,1520ms raw overrun. No audio/classroom-frame review; ASR negation and referents remain uncertain.'
}
entries = json.loads((root/'acquisition.json').read_text())
for entry in entries:
    if not entry.get('file'):
        entry.update(scope='Assigned original Nielsen page unavailable: originalHTTP and HTTPSwww/non-www initial attempts404; one user-requested retry also404, redirect final URL recorded. No original-page body or comments read; separate UBC substitute reviewed.',
                     license='Original-page authorization could not be checked because404; no permission inferred.',reviewed_at=now)
        entry['final_url'] = entry['attempts'][-1].get('final_url')
        continue
    name = Path(entry['file']).name
    assert digest(sources/entry['file']) == entry['sha256']
    entry.update(status='reviewed',reviewed_at=now,scope=scopes[name])
    if name in ('l-bitcoin.txt','bitcoin-faq.txt'):
        entry['license'] = dict(label='CC BY3.0US',evidence_file='home-2021.html',evidence_line=55,
            url='https://creativecommons.org/licenses/by/3.0/us/',scope='Course-authored text only; not external paper/video.')
    elif name in ('bitcoin.pdf','nielsen.pdf'):
        entry['license'] = 'No explicit full-translation permission found in the fetched PDF text/pages; original Chinese analytical reading only; no public reproduction of page images.'
        entry['license_scope_note'] = 'Each assigned reading checked separately; course CC license and third-party hosting do not establish external-work translation permission.'
    else:
        entry['license'] = meta['license']
        entry['license_note'] = 'Independent metadata query; exact CC version not exposed; not inherited from course site.'
    if name == 'video.en-orig.json3':
        entry.update(language='en-orig',caption_type='original-language English automatic ASR')
    if name == 'nielsen.pdf':
        entry['original_url_status'] = 'blocked404'
        entry['substitute_status'] = 'reviewed_complete_article_in_2015_snapshot_with_explicit_original_revision_and_comments_limits'
assert len({e['id'] for e in entries}) == len(entries)

derived = []
def add_derived(rel,parent,status,scope):
    p = root/rel
    derived.append(dict(id='lec19-2021-derived-'+rel.replace('/','-'),file='p7-lec19/'+rel,
        sha256=digest(p),status=status,generated_at=datetime.fromtimestamp(p.stat().st_mtime,timezone.utc).isoformat(),
        derived_from='p7-lec19/'+parent,scope=scope))
for rel,status,scope in [
    ('captions/captions.normalized.json','reviewed','All cue text read via lossless grouping; four targeted ranges directly reinspected; structure checked.'),
    ('captions/transcript.en.txt','reviewed','All text content read via lossless grouping, not independently reread in this equivalent timed representation.'),
    ('captions/captions.en.vtt','fetched','Generated only; no playback or independent line reading.'),
    ('captions/reading-by-minute.txt','reviewed','All248 lines,83 nonempty minute groups read sequentially; concatenation equals all2163 cue texts.')]:
    add_derived(rel,'video.en-orig.json3',status,scope)
add_derived('bitcoin.layout.txt','bitcoin.pdf','reviewed','All485 lines read, including references; actual figures/equations checked separately.')
add_derived('nielsen.layout.txt','nielsen.pdf','reviewed','All736 lines read in ranges1–420,421–736, interpreted in per-page column order; full essay and footnote; no comments. PDF images checked to recover mathematical images absent from extraction.')
bitcoin_pages = {
    2:'Ownership-signature chain and timestamp-chain diagrams; verify/sign arrows distinct from hash commitment.',
    3:'PoW block diagram, six network steps, valid/unspent requirement, cumulative-work meaning.',
    4:'Merkle tree before/after pruningTx0–2, retained sibling commitments and80*6*24*365=4.2MB header-only equation.',
    5:'SPV header-chain/Merkle path and separate input/output combining diagram; SPV limitation and typical-not-mandatory two outputs.',
    6:'Privacy-model pair as one group; piecewise gambler-ruin formula and p/q definitions; invalid transactions remain rejected.',
    7:'Lambda=zq/p, infinite-tail and finite sum formulas, assumptions, new-key paragraph and C code visually checked.',
    8:'All three numerical lists with q/z/P and thresholds; conclusion; no mislabeled chart axes.'}
nielsen_pages = {
    1:'Combined-PDF title mismatch and exact Bitcoin essay start/title/date, left/right column continuation.',
    2:'Signed intent, serial numbers, trusted-bank checks and decentralized ledger text.',
    3:'Sybil example, queue examples and image-based h symbol at end.',
    4:'All visible x/l/nonce formulas,4250 hash,16^10≈10^12; extraction drops image formulas; some standalone variables blank on actual page.',
    5:'Three block/fork diagrams, hash arrows,10^-8 satoshi expression and25BTC2013 context.',
    6:'Double-spend fork diagram,1/100^6=10^-12 specific-event equation,6confirmation definition and author questions.',
    7:'Two MultiBit screenshots0.06555555BTC/about70USD and receiving address; nonce x=0,x=1,x=2 sequences;0.31900000 image; actual transaction lines1–11.',
    8:'Remaining first transaction and all field explanations, coinbase/genesis caveats and malleability admission; second transaction begins.',
    9:'Full three-input/two-output code continuing p8,552bytes,0.01068000/4.00000000 outputs,change0.2→0.15+0.05; conclusion/privacy.',
    10:'Conclusion/omissions/scripting and footnote end; unrelated neural-network announcement distinguished; no comment section or explicit license.'}
for stem,scopes_by_page in [('bitcoin',bitcoin_pages),('nielsen',nielsen_pages)]:
    for p in sorted((root/(stem+'-pages')).glob('page-*.png')):
        page = int(p.stem.split('-')[1])
        add_derived(str(p.relative_to(root)),stem+'.pdf','reviewed' if page in scopes_by_page else 'fetched',
            scopes_by_page.get(page,'Rendered only; complete page text read in extraction, no independent image review.'))

inventory = json.loads((sources/'schedule-inventory-2021.json').read_text())
scheduled = next(x for x in inventory['lectures'] if x['id'] == 'lec19')
assert 'yB6m8EjAqPU' in scheduled['videos'][0]
for rel in scheduled['notes']+scheduled['readings']+scheduled['faq']:
    url = rel if rel.startswith('http') else inventory['url_base']+rel
    assert any(e['url'] == url and e['status'] in ('reviewed','partial','blocked') for e in entries)
for p in lecture.glob('*.md'):
    text = p.read_text()
    assert text.startswith('---\n') and '\nstatus:' in text
    assert text.count('```') % 2 == 0 and all(line.rstrip() == line for line in text.splitlines())
    for other,view in re.findall(r'#/c/mit-6\.824-2021/lec/([^?\s)]+)\?v=(\w+)',text):
        assert (course/'lectures'/other/(view+'.zh.md')).is_file(), (other,view)
    for image in re.findall(r'!\[[^]]*\]\(([^)]+)\)',text):
        assert (p.parent/image).is_file()
assert {p.name for p in lecture.glob('*.md')} == {'notes.zh.md','draft.zh.md','materials.zh.md'}

video = dict(video_id=meta['id'],url=meta['webpage_url'],metadata=meta,
    metadata_file='p7-lec19/metadata.json',normalized_caption_file='p7-lec19/captions/captions.normalized.json',
    raw_caption_file='p7-lec19/video.en-orig.json3',caption_time_structure=stats,
    draft_segment_count=len(segments),draft_segments=segments)
fragment = dict(course_id='mit-6.824-2021',lecture_id='lec19',batch='P7',
    content_status='completed_for_available_text_and_both_readings_with_explicit_original_site404_and_snapshot_limits',
    review_file='p7-lec19/review.txt',acquisition_file='p7-lec19/acquisition.json',retry_file='p7-lec19/retry-result.json',
    sources=entries,derived_files=derived,videos=[video],caption_time_structure=stats,draft_segments=segments,
    paper_visual_review=dict(bitcoin=dict(pdf_pages=9,read_pages=list(range(1,10)),inspected_page_images=sorted(bitcoin_pages),
        unnumbered_diagram_groups=7,numerical_lists=3,formula_pages=[4,6,7]),
        nielsen=dict(pdf_pages=10,essay_scope='p1 lower-left title through p10 conclusion and right-column footnote',
        inspected_page_images=list(range(1,11)),figures=6,formula_pages=[3,4,5,6,7],comments_read=False,
        original_site_status='404_after_three_initial_variants_and_one_requested_retry',substitute='UBC2015fivefiltersPDF')),
    version_mapping_evidence=dict(file='schedule-2021.html',scope='Lines249–250 read;2021-05-11L19 exact video,outline,FAQ and two assigned readings matched inventory. Shared files read-only.'),
    content_paths=[str(p.relative_to(course)) for p in sorted(lecture.glob('*.md'))],
    validation=dict(source_hashes='passed',derived_hashes='generated',metadata_whitelist='passed',caption_structure='passed_with_retained1520ms_overrun',
        lossless_grouping='passed',continuous_draft_timeline='passed',markdown_routes_and_images='passed',
        build='Not run by restricted worker; main agent integrates.',experiments='Not run',
        lab_commit='513cac0aef010750fc74688da8a395974a83cf7a',no_media_download=True,
        no_full_player_response_saved=True,no_cookies_saved=True,no_signed_media_urls_saved=True),
    issues=[
        'All2163 ASR texts read; no audio/classroom-frame verification. SHA-1 at08:29, attack-can-win negation around78min and final demonstrative referent unresolved.',
        '136 caption-union gaps,total292866ms,max11000ms; not silence detection. No breakout. Program crash near74:44; raw final end4965520ms exceeds duration by1520ms.',
        '69:40 ASR thousandsTPS conflicts with1MB/10min; outline separates4000TPS CPU verification bound. Draft retains discrepancy and dimensional example, not false chain-throughput claim.',
        'Longest means greatest valid accumulated work, not blindly most blocks; permission/signature,UTXO validation and fork choice separated.',
        'Honest majority means hashpower,not identities; finite confirmations probabilistic and do not solve arbitrary long partition/eclipse; majority attacker cannot forge signatures under assumptions.',
        'CPU-month is expectation illustration,not actual work certificate;ten-minute target not deadline;coinbase not transfer from pre-mined ordinary pool;nonce-only finite range caveat retained.',
        'Timestamp validation window/retarget period not specified by lecturer;soft/hard fork explanation limited;student stock-split price analogy not conservation law;not patched with unsourced modern facts.',
        'OriginalNielsenHTTP/HTTPS variants404 plus explicit requestedretry404. UBC2015third-party full essay read,not original live page;no comments available/read;some isolated variables missing in PDF itself.',
        'NielsenPDF contains neighboring unrelated posts and misleading first title. PDF metadataPDFNewspaper,actual essay2013-12-06,snapshot2015-03-27 distinguished;all6article images seen.',
        'Both readings lack confirmed full-translation permission;independently assessed,original analytical notes only. VideoCCAttribution exact version absent.',
        'Whitepaper2008 vsPDFcreation2009/server2021;outline2021L19/FAQno-year withsameLastModified2021-05-11;25BTC(Nielsen),12.5BTC(FAQ),6.25BTC(class) retained as different historical values.',
        'Gambler-ruin known-deficit formula distinct from Poisson unknown-progress model;6confirmation counting and paperz convention not silently equated;1/100^6 is one event,not full attack probability.',
        'Nielsen author questions not a proven2PC replacement,variance attack ornonce optimization;transaction JSON is shortened decoded example,not raw-wire spec;lock_time0 not irreversible finality.',
        'UTXO current-state validation,archival bootstrap andSPV inclusion proof distinguished;genesis/sighash/malleability modern details not inferred.',
        'No bibliography-linked fulltexts,current products,mine-network measurements or lab execution;2026fixedlabcommitunchanged.'
    ])
(root/'manifest-fragment.json').write_text(json.dumps(fragment,ensure_ascii=False,indent=2)+'\n')
summary = {k:v for k,v in stats.items() if k != 'all_uncovered_gaps'}
summary.update(source_records=len(entries),fetched_and_reviewed_source_files=sum(bool(e.get('file')) for e in entries),derived_files=len(derived))
(root/'validation.txt').write_text(json.dumps(summary,ensure_ascii=False,indent=2)+'\nPASS: local source hashes, whitelisted metadata, schedule links, lossless full-caption grouping, draft timeline, Markdown/local routes. No shared build, lab tests, audio or video-frame review.\n')
print(json.dumps(summary,ensure_ascii=False,indent=2))
