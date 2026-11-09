"""Fetch assigned historical sources and only whitelisted video metadata/ASR."""
import concurrent.futures
import hashlib
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from urllib.request import Request, urlopen

ROOT = Path(__file__).parent
VIDEO = 'https://www.youtube.com/watch?v=qXb5rDGqFdc'
SCHEDULE_VIDEO = 'https://youtu.be/qXb5rDGqFdc'

def record(path, url, modified=None):
    return dict(id='lec16-2021-'+path.name, url=url,
        retrieved_at=datetime.now(timezone.utc).isoformat(), last_modified=modified,
        file='p7-lec16/'+str(path.relative_to(ROOT)),
        sha256=hashlib.sha256(path.read_bytes()).hexdigest(), status='fetched')

def document(spec):
    folder, name = spec
    url = f'http://nil.csail.mit.edu/6.824/2021/{folder}/{name}'
    with urlopen(url, timeout=90) as response:
        data, modified = response.read(), response.headers.get('Last-Modified')
        final_url = response.geturl()
    path = ROOT/name
    path.write_bytes(data)
    return dict(record(path, url, modified), final_url=final_url)

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
    entries = [record(path,SCHEDULE_VIDEO),record(ROOT/'video.en-orig.json3',SCHEDULE_VIDEO)]
    for entry in entries:
        entry['last_modified_note'] = 'Not exposed by yt-dlp; unknown.'
        entry['request_url'] = VIDEO
        entry['final_url'] = metadata['webpage_url']
    return entries

if __name__ == '__main__':
    if '--headers-only' in sys.argv:
        # Supplement original response URLs without re-downloading successful snapshots.
        entries = json.loads((ROOT/'acquisition.json').read_text())
        observations = []
        for entry in entries:
            if entry['url'].startswith('http://nil.csail.mit.edu/'):
                with urlopen(Request(entry['url'], method='HEAD'), timeout=90) as response:
                    observation = dict(url=entry['url'], final_url=response.geturl(),
                        observed_at=datetime.now(timezone.utc).isoformat(),
                        last_modified=response.headers.get('Last-Modified'), method='HEAD')
                assert observation['last_modified'] == entry['last_modified']
                observations.append(observation)
                entry['final_url'] = observation['final_url']
                entry['final_url_observed_at'] = observation['observed_at']
                entry['final_url_note'] = 'Separate HEAD observation; original GET bytes and retrieval time retained.'
            else:
                entry.update(url=SCHEDULE_VIDEO, request_url=VIDEO, final_url=VIDEO)
        (ROOT/'header-observations.json').write_text(json.dumps(observations,indent=2)+'\n')
        (ROOT/'acquisition.json').write_text(json.dumps(entries,indent=2)+'\n')
        print('HEAD-only URL observations saved; source bytes unchanged.')
        sys.exit(0)
    with concurrent.futures.ThreadPoolExecutor() as pool:
        vf = pool.submit(video)
        entries = list(pool.map(document,[('notes','l-spark.txt'),('papers','zaharia-spark.pdf'),('papers','spark-faq.txt')]))+vf.result()
    (ROOT/'acquisition.json').write_text(json.dumps(entries,indent=2)+'\n')
    print(json.dumps(entries,indent=2))
