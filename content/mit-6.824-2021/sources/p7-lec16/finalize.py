"""Check only L16 local provenance, timeline and documents; emit integration fragment."""
import hashlib
import json
import re
from datetime import datetime, timezone
from pathlib import Path

root = Path(__file__).resolve().parent
sources = root.parent
course = sources.parent
lecture = course/'lectures/lec16'
now = datetime.now(timezone.utc).isoformat()

def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

def stamp_ms(stamp):
    m, s = map(int, stamp.split(':'))
    return (m*60+s)*1000

meta = json.loads((root/'metadata.json').read_text())
assert meta['id'] == 'qXb5rDGqFdc' and meta['duration'] == 4728
assert set(meta) == {'id','title','duration','channel','channel_id','uploader','upload_date','license','webpage_url'}
assert meta['title'] == 'Lecture 16: Big Data: Spark'
assert meta['upload_date'] == '20210430'
assert meta['channel'] == 'MIT 6.824: Distributed Systems'
cues = json.loads((root/'captions/captions.normalized.json').read_text())
draft = (lecture/'draft.zh.md').read_text()
segments = [dict(start=a, end=b, start_ms=stamp_ms(a), end_ms=stamp_ms(b), title=t)
    for a,b,t in re.findall(r'^## (\d+:\d{2})–(\d+:\d{2}) (.+)$', draft, re.M)]
duration = meta['duration']*1000
assert segments[0]['start_ms'] == 0 and segments[-1]['end_ms'] == duration
assert all(a['end_ms'] == b['start_ms'] for a,b in zip(segments,segments[1:]))
assert all(s['end_ms'] > s['start_ms'] for s in segments)
assert len(cues) == 2026
assert all(a['start_ms'] <= b['start_ms'] for a,b in zip(cues,cues[1:]))
assert all(c['end_ms'] >= c['start_ms'] >= 0 for c in cues)
assert all(sum(s['start_ms'] <= c['start_ms'] < s['end_ms'] for s in segments) == 1 for c in cues)
for s in segments:
    selected = [(i+1,c) for i,c in enumerate(cues) if s['start_ms'] <= c['start_ms'] < s['end_ms']]
    s.update(cue_count=len(selected), first_cue=selected[0][0] if selected else None,
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
stats = dict(cue_count=len(cues), first_start_ms=cues[0]['start_ms'],
    last_start_ms=cues[-1]['start_ms'], last_end_ms=cues[-1]['end_ms'],
    metadata_duration_seconds=meta['duration'], starts_monotonic=True,
    ends_monotonic=all(a['end_ms'] <= b['end_ms'] for a,b in zip(cues,cues[1:])),
    negative_duration_count=0,
    cues_ending_after_video=sum(c['end_ms'] > duration for c in cues),
    tail_overrun_ms=max(0,end-duration), tail_uncaptioned_ms=max(0,duration-end),
    overlapping_adjacent_cue_pairs=sum(a['end_ms'] > b['start_ms'] for a,b in zip(cues,cues[1:])),
    positive_uncovered_gap_count=len(gaps), uncovered_ms_within_video=duration-covered,
    maximum_uncovered_gap_ms=max(g['duration_ms'] for g in gaps), all_uncovered_gaps=gaps,
    draft_segment_count=len(segments), draft_start=segments[0]['start'], draft_end=segments[-1]['end'],
    audio_reviewed=False, video_frames_reviewed=False,
    interpretation='All 2026 cue texts read sequentially through lossless minute grouping. Interval-union gaps are not silence detection or proof of missing speech. No breakout discussion in available transcript. Environment interruption near02min retained. Raw final2000ms overrun retained; no audio/classroom frame review.')
assert len(gaps) == 127 and duration-covered == 216290
assert stats['maximum_uncovered_gap_ms'] == 11000 and stats['tail_overrun_ms'] == 2000

scopes = {
    'l-spark.txt': 'All219 lines read. Internal title6.8242021Lecture16; PageRank Scala setup/distinct/groupByKey/cache, local command/output, shell commands, lineage, scheduling/shuffle, optimization and recovery. Shell execution/output not present in video ASR and not claimed as video demo. Last-Modified2021-05-04 is after class2021-04-29. No current Spark implementation fetched.',
    'spark-faq.txt': 'All135 lines and every Q/A read, including reuse, immutable versions, energy discussion, location metadata, Scala closures, single-scan limitations, hash partitioning and historical DataFrame wording. Last-Modified2021-04-30 after class; heading Spark FAQ has no year. Linked commercial sites, Naiad/SparkStreaming/FAWN/Piccolo and latest API pages not read.',
    'zaharia-spark.pdf': 'All14 PDF pages read: abstract,sections1-9,acknowledgements,all33 bibliography entries. All1244 layout text lines read sequentially in1-360,361-720,721-1244 with two-column/page continuation understood. All14 figures,3 tables,logistic-regression code formula and PageRank formula visually checked on actual rendered pages3-11; page1 title also inspected. Definition/checkpoint/scheduler and figure numerical disagreements explicitly resolved or retained. Bibliography full texts not read.',
    'metadata.json': 'All whitelist fields independently acquired and checked: qXb5rDGqFdc; Lecture16:BigData:Spark;4728s/78:48;MIT6.824:DistributedSystems;channelUC_7WrbZTCODu1o_kfUMq88g;upload20210430;CreativeCommonsAttributionlicense(reuseallowed),exact version absent. Original schedule URL preserved; canonical request URL separate.',
    'video.en-orig.json3': 'All2026 original-English automatic cue texts read in order via79 lossless minute groups,reading-by-minute.txt lines1-90,91-180,181-236. Full available lecture plus55min-onward post-class Q/A including FaRM61-65min and unresolved narrow-dependency debate65-71min. Direct cue reinspection15:00-20:30 collect/count,51:00-52:20 only-final-collect claim,56:45-57:50 driver/scheduler uncertainty. First0ms,last start4726640,last end4730000,2 cues exceed4728000ms. No audio/video-frame review.'
}
entries = json.loads((root/'acquisition.json').read_text())
for entry in entries:
    name = Path(entry['file']).name
    assert digest(sources/entry['file']) == entry['sha256']
    assert entry.get('final_url')
    entry.update(status='reviewed',reviewed_at=now,scope=scopes[name])
    if name in ('l-spark.txt','spark-faq.txt'):
        entry['license'] = dict(label='CC BY 3.0 US',evidence_file='home-2021.html',
            evidence_scope='Existing homepage line55 checked; only course-authored text, not paper/video.',
            url='https://creativecommons.org/licenses/by/3.0/us/')
    elif name == 'zaharia-spark.pdf':
        entry['license'] = 'Full-translation permission unconfirmed; original analytical Chinese reading, no full translation/public page-image reproduction.'
        entry['pdf_pages_read'] = list(range(1,15))
    else:
        entry['license'] = meta['license']
        entry['license_note'] = 'Video-specific independent metadata; exact CC version absent.'
    if name == 'video.en-orig.json3':
        entry.update(language='en-orig',caption_type='original-language automatic English ASR')
assert len({e['id'] for e in entries}) == len(entries)
inventory = json.loads((sources/'schedule-inventory-2021.json').read_text())
scheduled = next(x for x in inventory['lectures'] if x['id'] == 'lec16')
assert scheduled['videos'] == ['https://youtu.be/qXb5rDGqFdc']
for part in scheduled['notes']+scheduled['readings']+scheduled['faq']:
    assert any(e['url'] == inventory['url_base']+part for e in entries)

derived = []
def derived_record(rel,source_name,status,scope):
    p = root/rel
    upstream = next(e for e in entries if Path(e['file']).name == source_name)
    return dict(id='lec16-2021-derived-'+rel.replace('/','-'),file='p7-lec16/'+rel,
        sha256=digest(p),status=status,generated_at=datetime.fromtimestamp(p.stat().st_mtime,timezone.utc).isoformat(),
        derived_from=upstream['file'],url=upstream['url'],retrieved_at=upstream['retrieved_at'],
        last_modified=upstream['last_modified'],scope=scope)

for rel,status,scope in [
    ('captions/captions.normalized.json','reviewed','All cue content read through lossless grouping; selected raw timed cues rechecked and all timing structure checked.'),
    ('captions/transcript.en.txt','reviewed','Generated timed text; all cue content read via lossless grouping, not separately reread in this representation.'),
    ('captions/captions.en.vtt','fetched','Generated only; not played or independently line-read.'),
    ('captions/reading-by-minute.txt','reviewed','All236 lines/79 nonempty minute groups read sequentially; concatenation exactly equals all2026 cue texts.'),
    ('zaharia-spark.layout.txt','reviewed','All1244 lines read including33 bibliography entries; formulas/figures checked against pages.')]:
    derived.append(derived_record(rel,'zaharia-spark.pdf' if rel.startswith('zaharia') else 'video.en-orig.json3',status,scope))
page_scopes = {
    1:'Actual internal title, authors, abstract and historical paper identity; no blanket CC/full-translation permission inferred.',
    3:'Figure1 log lineage and exact collect/count/code indexing; Table1 all comparison rows and notes.',
    4:'Figure2 driver/workers/RAM/input/tasks/results; closure-capture footnote.',
    5:'Table2 all transformation/action signatures; Figure3 PageRank versions; logistic-regression formula/code and alpha/N PageRank formula, immutable-variable footnote.',
    6:'Table3 five representation methods; exact parent-to-child narrow-dependency definition; RELIABLE flag, partitioning and contribution-aggregation wording.',
    7:'Figures4-5 all partition arrows and cached-black-partition/stage labels; join mixed narrow/wide cases; shuffle materialization; explicit no scheduler-failure tolerance.',
    8:'Figure6 closure/reference graph; exact RDD LRU exception, storage choices; REPLICATE flag vs page6RELIABLE; auto checkpoint future work.',
    9:'Figures7-8 all first/later and25/50/100-node bars,seconds and algorithm/implementation legends;up-to20x versus specific25.3x/20.7x results.',
    10:'Figures9-11 all bars/units;single-machine256MB input-format comparison;PageRank30/60nodes;fault iteration6 graph81s vs prose80s;conditions75nodes/400tasks.',
    11:'Figures12-14 all percentages/node counts/data sizes,units/legends/error bars;Twitter10^7 exponent;query100GB/500GB/1TB distinction and distinct hardware.'
}
for p in sorted((root/'paper-pages').glob('page-*.png')):
    page = int(p.stem.split('-')[1])
    derived.append(derived_record(str(p.relative_to(root)),'zaharia-spark.pdf',
        'reviewed' if page in page_scopes else 'fetched',
        page_scopes.get(page,'Rendered only; full page text read through extraction, image not independently inspected.')))
headers = root/'header-observations.json'
derived.append(dict(id='lec16-2021-head-observations',file='p7-lec16/header-observations.json',
    sha256=digest(headers),status='reviewed',scope='Separate HEAD requests confirm final URLs and Last-Modified for all3 existing official source snapshots; did not redownload bodies or alter original GET timestamps.',
    observations=json.loads(headers.read_text())))

documents = []
for p in sorted(lecture.glob('*.md')):
    text = p.read_text()
    assert text.startswith('---\n') and text.count('```') % 2 == 0
    assert all(line == line.rstrip() for line in text.splitlines())
    for ident,view in re.findall(r'#/c/mit-6\.824-2021/lec/([^?\s)]+)\?v=(\w+)',text):
        assert (course/'lectures'/ident/(view+'.zh.md')).is_file(), (ident,view)
    for image in re.findall(r'!\[[^]]*\]\(([^)]+)\)',text):
        assert (p.parent/image).is_file()
    documents.append(dict(file=str(p.relative_to(course)),sha256=digest(p),status='completed'))
assert {p.name for p in lecture.glob('*.md')} == {'notes.zh.md','draft.zh.md','materials.zh.md'}
video = dict(video_id=meta['id'],url=scheduled['videos'][0],metadata=meta,
    metadata_file='p7-lec16/metadata.json',normalized_caption_file='p7-lec16/captions/captions.normalized.json',
    caption_file='p7-lec16/video.en-orig.json3',caption_time_structure=stats,
    draft_segment_count=len(segments),draft_segments=segments,status='reviewed_text',
    review_scope=scopes['video.en-orig.json3'])
fragment = dict(course_id='mit-6.824-2021',lecture_id='lec16',batch='P7',
    content_status='completed_for_available_text_with_explicit_ASR_and_historical_implementation_limits',
    review_file='p7-lec16/review.txt',acquisition_file='p7-lec16/acquisition.json',
    sources=entries,derived_files=derived,videos=[video],
    caption_time_structure=stats,draft_segments=segments,
    paper_visual_review=dict(pdf_pages=14,figures=list(range(1,15)),tables=list(range(1,4)),
        inspected_page_images=sorted(page_scopes),formula_pages=[5],audio_or_classroom_frames=False),
    version_mapping_evidence=dict(file='schedule-2021.html',scope='Lines229-230 checked:2021-04-29L16 exact outline/paper/FAQ/video links;inventory matches. Source URLs preserve schedule originals;redirect/canonical endpoints separate.'),
    documents=documents,content_paths=[d['file'] for d in documents],
    lab_code_commit='513cac0aef010750fc74688da8a395974a83cf7a',lab_tests='not_run',update_ray='not_started',
    validation=dict(source_hashes='passed',caption_structure='passed_with_retained_raw2000ms_tail_overrun',
        lossless_grouping='passed',continuous_draft_timeline='passed',markdown_local_structure='passed',
        integration_contract='videos[0] metadata object and sources-relative paths present; full check-p7 delegated to main agent.',
        build='Not run by restricted worker.',experiments='Not run',
        no_media_download=True,no_full_player_response_saved=True,no_signed_urls_saved=True,no_cookies_saved=True),
    issues=[
        'No audio/classroom-frame verification; ASR numbers/negations/board details remain uncertain. No invented breakout discussion or shell demo.',
        '127 interval-union gaps total216290ms,max11000ms;environment pause near02min;raw final4730000ms exceeds4728000ms by2000ms,2 cues end after duration.',
        'Video-specific CC Attribution exact version absent;paper full-translation permission unconfirmed.',
        'Outline internal2021L16 title but Last-ModifiedMay4 afterApr29class;FAQ no-year heading/Apr30modified;PDF2012paper vsJan22,2021server snapshot date.',
        'Narrow definition constrains parent fanout,not child input count;classroom65-71min disagreement unresolved in video but paperpp6-7 consistent and used for correction.',
        'PageRank co-partitioned join does not eliminate contribution reduceByKey shuffle;only-final-collect claim51:45 corrected explicitly.',
        'collect returns elements,count counts;classroom16-20min conflates them;Scala index3 is not a proof of three-piece split.',
        '2012paper explicitly lacks scheduler-failure tolerance;57min classroom reconnect speculation/ASR uncertainty not a guarantee.',
        'persist/cache,shuffle intermediate materialization,and durable checkpoint distinguished;RELIABLEp6vsREPLICATEp8 historical naming discrepancy retained;automatic checkpoint future work.',
        'Paper alpha/N normalized PageRank vs2021outline0.15+0.85sum with initial1 scores distinguished;dangling-node handling not supplied by short example.',
        'Figure11 graph81s vs prose80s retained;Figure9 single-machine256MB differs from100GB cluster tests;Figure14 hardware differs from default.',
        'FaRM61-65min follow-up retained as classroom Q/A;not a new full protocol review or replacement for L15.',
        'FAQ modern/deprecated and lecture product statements treated as historical;external linked papers/currentSpark/thesis not read. Ray remains future/uncompleted.',
        'Fixed2026lab commit retained;no Spark execution,lab tests,shared-file writes,build,staging or commits.'
    ])
(root/'manifest-fragment.json').write_text(json.dumps(fragment,ensure_ascii=False,indent=2)+'\n')
summary = {k:v for k,v in stats.items() if k != 'all_uncovered_gaps'}
(root/'validation.txt').write_text(json.dumps(summary,ensure_ascii=False,indent=2)+'\nPASS: local source hashes, exact schedule URLs, metadata whitelist, lossless reading groups, cue intervals, continuous draft timeline, Markdown routes and document hashes. No audio/frame, Spark, build, git or lab execution.\n')
print(json.dumps(summary,ensure_ascii=False,indent=2))
