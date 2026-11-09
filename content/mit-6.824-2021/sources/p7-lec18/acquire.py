"""Fetch schedule-assigned sources and whitelist-only original-language captions."""
import concurrent.futures
import hashlib
import json
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from urllib.request import urlopen

ROOT = Path(__file__).parent
VIDEO = 'https://www.youtube.com/watch?v=FxwjSs_xSBM'

def record(path, url, modified=None, final_url=None):
    return dict(id='lec18-2021-'+path.name, url=url,
        retrieved_at=datetime.now(timezone.utc).isoformat(), last_modified=modified, final_url=final_url,
        file='p7-lec18/'+str(path.relative_to(ROOT)),
        sha256=hashlib.sha256(path.read_bytes()).hexdigest(), status='fetched')

def document(spec):
    folder, name = spec
    url = f'http://nil.csail.mit.edu/6.824/2021/{folder}/{name}'
    with urlopen(url, timeout=90) as response:
        data, modified = response.read(), response.headers.get('Last-Modified')
        final_url = response.geturl()
    path = ROOT/name
    path.write_bytes(data)
    return record(path,url,modified,final_url)

def video():
    keys=['id','title','duration','channel','channel_id','uploader','upload_date','license','webpage_url']
    template='{'+','.join(json.dumps(k)+':%('+k+')j' for k in keys)+'}'
    result=subprocess.run(['yt-dlp','--skip-download','--no-simulate','--no-write-info-json',
        '--write-subs','--write-auto-subs','--sub-langs','en-orig','--sub-format','json3',
        '--print',template,'-o',str(ROOT/'video.%(ext)s'),VIDEO],capture_output=True,text=True)
    if result.returncode:
        raise RuntimeError('yt-dlp failed; exit='+str(result.returncode))
    meta=next(json.loads(line) for line in result.stdout.splitlines() if line.startswith('{"id"'))
    path=ROOT/'metadata.json'
    path.write_text(json.dumps(meta,ensure_ascii=False,indent=2)+'\n')
    return [record(path,VIDEO),record(ROOT/'video.en-orig.json3',VIDEO)]

if __name__=='__main__':
    with concurrent.futures.ThreadPoolExecutor() as pool:
        vf=pool.submit(video)
        entries=list(pool.map(document,[('notes','l-sundr.txt'),('papers','li-sundr.pdf'),('papers','sundr-faq.txt')]))+vf.result()
    (ROOT/'acquisition.json').write_text(json.dumps(entries,indent=2)+'\n')
    print(json.dumps(entries,indent=2))
