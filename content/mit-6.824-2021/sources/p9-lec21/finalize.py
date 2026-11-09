"""Finalize local provenance and minimal checks after actual source reading.

Run only after reading the source scopes recorded below. No project experiments.
"""
import hashlib
import json
import re
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).parent
COURSE = ROOT.parent.parent
LECTURE = COURSE/'lectures/lec21'
NOW = datetime.now(timezone.utc).isoformat()

def load(path):
    return json.loads(path.read_text())

def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

def milliseconds(stamp):
    m,s = map(int,stamp.split(':'))
    return (m*60+s)*1000

metadata = load(ROOT/'metadata.json')
cues = load(ROOT/'captions.normalized.json')
duration = metadata['duration']*1000
assert metadata['id'] == 'bu41Qt9G5Qo'
assert set(metadata) == {'id','title','duration','channel','channel_id','uploader','upload_date','license','webpage_url'}
assert all(c['end_ms'] >= c['start_ms'] >= 0 for c in cues)
assert all(a['start_ms'] <= b['start_ms'] for a,b in zip(cues,cues[1:]))
gaps, covered_to = [], 0
for cue in cues:
    start,end = min(duration,cue['start_ms']),min(duration,cue['end_ms'])
    if start > covered_to:
        gaps.append(dict(start_ms=covered_to,end_ms=start,duration_ms=start-covered_to))
    covered_to = max(covered_to,end)
if covered_to < duration:
    gaps.append(dict(start_ms=covered_to,end_ms=duration,duration_ms=duration-covered_to))
segments = []
for start,end,title in re.findall(r'^## (\d+:\d{2})–(\d+:\d{2})｜(.+)$',(LECTURE/'draft.zh.md').read_text(),re.M):
    a,b = milliseconds(start),milliseconds(end)
    indexes = [i for i,c in enumerate(cues,1) if a <= c['start_ms'] < b]
    segments.append(dict(start=start,end=end,start_ms=a,end_ms=b,title=title,
                         cue_count=len(indexes),first_cue=indexes[0],last_cue=indexes[-1]))
assert segments[0]['start_ms'] == 0 and segments[-1]['end_ms'] == duration
assert all(a['end_ms']==b['start_ms'] for a,b in zip(segments,segments[1:]))
assert sum(s['cue_count'] for s in segments) == len(cues)
stats = dict(cue_count=len(cues),first_start_ms=cues[0]['start_ms'],last_start_ms=cues[-1]['start_ms'],
    last_end_ms=max(c['end_ms'] for c in cues),metadata_duration_seconds=metadata['duration'],
    starts_monotonic=True,ends_monotonic=all(a['end_ms']<=b['end_ms'] for a,b in zip(cues,cues[1:])),
    negative_duration_count=0,cues_ending_after_video=sum(c['end_ms']>duration for c in cues),
    tail_overrun_ms=max(0,max(c['end_ms'] for c in cues)-duration),
    tail_uncaptioned_ms=max(0,duration-max(c['end_ms'] for c in cues)),
    overlapping_adjacent_cue_pairs=sum(a['end_ms']>b['start_ms'] for a,b in zip(cues,cues[1:])),
    positive_uncovered_gap_count=len(gaps),uncovered_ms_within_video=sum(g['duration_ms'] for g in gaps),
    maximum_uncovered_gap_ms=max(g['duration_ms'] for g in gaps),all_uncovered_gaps=gaps,
    draft_segment_count=len(segments),draft_start=segments[0]['start'],draft_end=segments[-1]['end'],
    audio_reviewed=False,video_frames_reviewed=False,
    interpretation='Interval-union gaps clipped to metadata duration; no silence detection. All2829 cue texts sequentially read in98 lossless minute groups. Raw1280ms tail overrun retained; two cues exceed metadata duration. Draft headings cover themes with second-rounded transition boundaries, not continuous speech recovery.')

scopes = {
    'schedule-2021.html': 'Targeted read lines257-273;2021-05-20 L21 Project demos links bu41Qt9G5Qo, papers/katabi-analogicfs.pdf and papers/analogicfs-faq.txt; Last day of classes. No lecture-outline link. Historical/full schedule scope belongs to main agent.',
    'home-2021.html': 'Targeted lines45-59; license link at line55 is CC BY3.0US. No assumption that course license covers external paper/video.',
    'katabi-analogicfs.pdf': 'Entire7pages read through335-line layout extraction; actual page images1-7 independently inspected, including all5figures, malformed (n^2) complexity fragment, section1-6 and32 bibliography entries. Title and displayed author names transcribed. FAQ establishes SCIgen-linked humorous assignment, not credible implemented system. No external bibliography full texts or SCIgen page read; no experiment reproduction.',
    'analogicfs-faq.txt': 'Entire8lines read. Single Q/A: fun/intriguing paper written in quotes by past6.824 TA, links SCIgen, course tradition and careful reading/belief. No individual author named; attributed to MIT6.824 course staff.',
    'metadata.json': 'Independent whitelist query: Lecture21: Project Presentations;5880s/98:00;MIT6.824: Distributed Systems;UC_7WrbZTCODu1o_kfUMq88g;upload20210520;CC Attribution reuse allowed, version unspecified.',
    'video.en-orig.json3': 'All2829 original-language English automatic cue texts read sequentially via98 lossless minute groups,293lines in ranges1-100,100-198,199-293. Transition cues around10:30,21:30,32:30,44:00,58:00,70:40,79:20,93:00,95:00 independently inspected. Eight projects, Q&A, voting follow-up, class closing and logistics; no audio or classroom-frame review.'
}
course_license = dict(label='CC BY3.0US',evidence_file='p9-lec21/home-2021.html',evidence_line=55,
    url='https://creativecommons.org/licenses/by/3.0/us/',scope='Course-authored text only; not extended to paper or video.')
sources = load(ROOT/'acquisition.json')
for entry in sources:
    name = Path(entry['file']).name
    assert digest(COURSE/'sources'/entry['file']) == entry['sha256']
    entry.update(status='reviewed',reviewed_at=NOW,scope=scopes[name])
    if name in ('schedule-2021.html','home-2021.html','analogicfs-faq.txt'):
        entry['license'] = course_license
    elif name.endswith('.pdf'):
        entry['license'] = 'Public full translation permission unconfirmed; original Chinese critical paraphrase only; page images local, not published.'
        entry['pdf_pages_read'] = list(range(1,8))
        entry['visually_reviewed_pages'] = list(range(1,8))
        entry['internal_title'] = 'Experiences with a Distributed, Scalable, Methodological File System: AnalogicFS'
        entry['displayed_authors'] = ['Leopold Katabi','Rudy Rhea','Callib Nagaos']
        entry['genre'] = 'SCIgen-linked humorous pseudo-paper, per course FAQ; not treated as implemented validated system'
    else:
        entry['license'] = metadata['license']
        entry['license_note'] = 'Independent video metadata; exact CC version not supplied.'
        if name.endswith('.json3'):
            entry.update(language='en-orig',caption_type='original-language automatic English ASR')

derived = []
for path in [ROOT/'captions.normalized.json',ROOT/'reading-by-minute.txt',ROOT/'katabi-analogicfs.layout.txt',*sorted((ROOT/'paper-pages').glob('*.png'))]:
    relative = path.relative_to(ROOT)
    is_caption = path.name in ('captions.normalized.json','reading-by-minute.txt')
    derived.append(dict(id='p9-lec21-derived-'+str(relative).replace('/','-'),file='p9-lec21/'+str(relative),sha256=digest(path),status='reviewed',
        generated_at=datetime.fromtimestamp(path.stat().st_mtime,timezone.utc).isoformat(),reviewed_at=NOW,
        derived_from='p9-lec21/'+('video.en-orig.json3' if is_caption else 'katabi-analogicfs.pdf'),
        scope=('All cue text sequentially read through lossless98 minute groups; normalized cue objects at project transitions directly inspected; time structure checked.' if is_caption else
               'Actual page image viewed; all7pages inspected, all5figures and complexity typography checked.' if path.suffix=='.png' else
               'Entire335lines read, all7pages, abstract, sections1-6 and32bibliography entries; dual-column continuations followed.')))

fragment = dict(course_id='mit-6.824-2021',lecture_id='lec21',batch='P9',
    content_status='completed_for_available_text_with_explicit_asr_and_audio_visual_limits',
    review_file='p9-lec21/review.txt',acquisition_file='p9-lec21/acquisition.json',sources=sources,derived_files=derived,
    videos=[dict(video_id=metadata['id'],url=metadata['webpage_url'],metadata=metadata,metadata_file='p9-lec21/metadata.json',
        normalized_caption_file='p9-lec21/captions.normalized.json',caption_time_structure=stats,
        draft_segment_count=len(segments),draft_segments=segments)],
    content_files=[dict(file=str(p.relative_to(COURSE)),sha256=digest(p)) for p in sorted(LECTURE.glob('*.zh.md'))],
    boundaries=['Subtitles only; no audio or video frames reviewed.','No student project repositories, programs or course labs run.',
        'Private analytics project name SIS/sis unconfirmed; turtle-themed editor name unconfirmed; sequence CRDT only tentatively LSEQ.',
        'Pinguino partition answers remain unresolved; no repair silently added.',
        'AnalogicFS independent same-day written reading; humorous pseudo-paper; no public full translation permission confirmed.'])
(ROOT/'manifest-fragment.json').write_text(json.dumps(fragment,ensure_ascii=False,indent=2)+'\n')
for path in LECTURE.glob('*.zh.md'):
    text = path.read_text()
    assert text.startswith('---\n') and '\nstatus:' in text
    assert all(line==line.rstrip() for line in text.splitlines())
    assert len(re.findall(r'^```',text,re.M))%2==0
    for ident,view in re.findall(r'#/c/mit-6\.824-2021/lec/([^?]+)\?v=(\w+)',text):
        assert (COURSE/'lectures'/ident/(view+'.zh.md')).is_file()
summary = dict(metadata=metadata,**{k:v for k,v in stats.items() if k!='all_uncovered_gaps'})
(ROOT/'validation.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2)+'\n')
print(json.dumps(summary,ensure_ascii=False,indent=2))
