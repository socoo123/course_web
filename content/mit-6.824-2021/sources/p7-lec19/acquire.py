"""Acquire assigned sources and only whitelisted YouTube metadata/English ASR."""
import concurrent.futures
import hashlib
import json
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from urllib.request import Request, urlopen

ROOT = Path(__file__).parent
VIDEO = 'https://www.youtube.com/watch?v=yB6m8EjAqPU'

def record(path, url, modified=None, **extra):
    return dict(id='lec19-2021-'+path.name, url=url,
        retrieved_at=datetime.now(timezone.utc).isoformat(), last_modified=modified,
        file='p7-lec19/'+str(path.relative_to(ROOT)),
        sha256=hashlib.sha256(path.read_bytes()).hexdigest(), status='fetched', **extra)

def document(spec):
    name, urls = spec
    attempts = []
    for url in urls:
        try:
            with urlopen(Request(url, headers={'User-Agent':'Mozilla/5.0'}), timeout=60) as r:
                data, modified, resolved = r.read(), r.headers.get('Last-Modified'), r.url
            path = ROOT/name
            path.write_bytes(data)
            return record(path, urls[0], modified, fetched_url=url, final_url=resolved, attempts=attempts)
        except Exception as e:
            attempts.append(dict(url=url, error=str(e)))
    return dict(id='lec19-2021-'+name, url=urls[0], status='blocked', attempts=attempts,
                retrieved_at=datetime.now(timezone.utc).isoformat(), last_modified=None, file=None, sha256=None)

def video():
    keys = ['id','title','duration','channel','channel_id','uploader','upload_date','license','webpage_url']
    template = '{'+','.join(json.dumps(k)+':%('+k+')j' for k in keys)+'}'
    r = subprocess.run(['yt-dlp','--skip-download','--no-simulate','--no-write-info-json',
        '--write-auto-subs','--sub-langs','en-orig','--sub-format','json3','--print',template,
        '-o',str(ROOT/'video.%(ext)s'),VIDEO],capture_output=True,text=True)
    if r.returncode:
        return [dict(id='lec19-2021-video',url=VIDEO,status='blocked',error='yt-dlp exit '+str(r.returncode))]
    meta = next(json.loads(line) for line in r.stdout.splitlines() if line.startswith('{"id"'))
    p = ROOT/'metadata.json'
    p.write_text(json.dumps(meta,ensure_ascii=False,indent=2)+'\n')
    return [record(p,VIDEO,last_modified_note='Not exposed by yt-dlp'),
            record(ROOT/'video.en-orig.json3',VIDEO,last_modified_note='Not exposed by yt-dlp')]

if __name__ == '__main__':
    base = 'http://nil.csail.mit.edu/6.824/2021/'
    specs = [(n,[base+folder+'/'+n]) for folder,n in [('notes','l-bitcoin.txt'),('papers','bitcoin.pdf'),('papers','bitcoin-faq.txt')]]
    specs.append(('nielsen.html',[
        'http://www.michaelnielsen.org/ddi/how-the-bitcoin-protocol-actually-works',
        'https://www.michaelnielsen.org/ddi/how-the-bitcoin-protocol-actually-works/',
        'https://michaelnielsen.org/ddi/how-the-bitcoin-protocol-actually-works/']))
    with concurrent.futures.ThreadPoolExecutor() as pool:
        vf = pool.submit(video)
        entries = list(pool.map(document,specs))+vf.result()
    (ROOT/'acquisition.json').write_text(json.dumps(entries,indent=2)+'\n')
    print(json.dumps(entries,indent=2))
