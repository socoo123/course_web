"""Acquire L21 sources; retain only whitelisted YouTube metadata, no media URLs."""
import concurrent.futures
import hashlib
import json
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from urllib.request import urlopen

ROOT = Path(__file__).parent
BASE = 'http://nil.csail.mit.edu/6.824/2021/'
VIDEO = 'https://www.youtube.com/watch?v=bu41Qt9G5Qo'

def record(path, url, modified=None, final_url=None):
    return dict(id='p9-lec21-'+path.name, url=url,
                retrieved_at=datetime.now(timezone.utc).isoformat(), last_modified=modified,
                file='p9-lec21/'+str(path.relative_to(ROOT)),
                sha256=hashlib.sha256(path.read_bytes()).hexdigest(), status='fetched',
                **({'final_url': final_url} if final_url else {}))

def document(spec):
    remote, name = spec
    with urlopen(BASE+remote, timeout=90) as response:
        data, modified, final = response.read(), response.headers.get('Last-Modified'), response.geturl()
    path = ROOT/name
    path.write_bytes(data)
    return record(path, BASE+remote, modified, final)

def video():
    keys = ['id','title','duration','channel','channel_id','uploader','upload_date','license','webpage_url']
    template = '{'+','.join(json.dumps(k)+':%('+k+')j' for k in keys)+'}'
    result = subprocess.run(['yt-dlp','--skip-download','--no-simulate','--no-write-info-json',
        '--write-auto-subs','--sub-langs','en-orig','--sub-format','json3','--print',template,
        '-o',str(ROOT/'video.%(ext)s'),VIDEO],capture_output=True,text=True)
    if result.returncode:
        raise RuntimeError('yt-dlp failed; exit='+str(result.returncode))
    metadata = next(json.loads(line) for line in result.stdout.splitlines() if line.startswith('{"id"'))
    path = ROOT/'metadata.json'
    path.write_text(json.dumps(metadata,ensure_ascii=False,indent=2)+'\n')
    entries = [record(path,VIDEO),record(ROOT/'video.en-orig.json3',VIDEO)]
    for entry in entries:
        entry['last_modified_note'] = 'Not exposed by yt-dlp; unknown.'
    return entries

if __name__ == '__main__':
    with concurrent.futures.ThreadPoolExecutor() as pool:
        vf = pool.submit(video)
        docs = list(pool.map(document, [('schedule.html','schedule-2021.html'),('', 'home-2021.html'),
            ('papers/katabi-analogicfs.pdf','katabi-analogicfs.pdf'),('papers/analogicfs-faq.txt','analogicfs-faq.txt')]))
        entries = docs+vf.result()
    (ROOT/'acquisition.json').write_text(json.dumps(entries,indent=2)+'\n')
    print(json.dumps(entries,indent=2))
