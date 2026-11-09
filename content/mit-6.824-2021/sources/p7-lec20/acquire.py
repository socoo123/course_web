"""Acquire only assigned historical documents and whitelisted video metadata/ASR."""
import concurrent.futures
import hashlib
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from urllib.request import urlopen

ROOT = Path(__file__).parent
VIDEO = 'https://www.youtube.com/watch?v=DnyBPxo3B6I'

def record(path, url, modified=None, final_url=None):
    return dict(id='lec20-2021-'+path.name, url=url,
                retrieved_at=datetime.now(timezone.utc).isoformat(), last_modified=modified,
                file='p7-lec20/'+str(path.relative_to(ROOT)),
                sha256=hashlib.sha256(path.read_bytes()).hexdigest(), status='fetched',
                **({'final_url': final_url} if final_url else {}))

def document(spec):
    folder, name = spec
    url = f'http://nil.csail.mit.edu/6.824/2021/{folder}/{name}'
    with urlopen(url, timeout=90) as response:
        data, modified = response.read(), response.headers.get('Last-Modified')
        final_url = response.geturl()
    path = ROOT/name
    path.write_bytes(data)
    return record(path, url, modified, final_url)

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
        vf = None if '--documents-only' in sys.argv else pool.submit(video)
        documents = list(pool.map(document,[('notes','l-blockstack.txt'),('papers','blockstack-atc16.pdf'),('papers','blockstack-faq.txt')]))
        retained = [e for e in json.loads((ROOT/'acquisition.json').read_text()) if Path(e['file']).name in ('metadata.json','video.en-orig.json3')] if vf is None else vf.result()
        entries = documents+retained
    (ROOT/'acquisition.json').write_text(json.dumps(entries,indent=2)+'\n')
    print(json.dumps(entries,indent=2))
