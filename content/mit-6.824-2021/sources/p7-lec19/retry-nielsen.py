"""One user-requested retry after a reported network interruption; keep old evidence."""
import json
from datetime import datetime, timezone
from pathlib import Path
from urllib.request import Request, urlopen
from urllib.error import HTTPError
from acquire import record

root = Path(__file__).parent
entries = json.loads((root/'acquisition.json').read_text())
entry = next(e for e in entries if e['id'] == 'lec19-2021-nielsen.html')
url = entry['url']
attempt = dict(url=url, retrieved_at=datetime.now(timezone.utc).isoformat(), reason='One retry explicitly requested after network interruption')
try:
    with urlopen(Request(url, headers={'User-Agent':'Mozilla/5.0'}), timeout=60) as response:
        path = root/'nielsen-retry.html'
        path.write_bytes(response.read())
        result = record(path,url,response.headers.get('Last-Modified'),final_url=response.url)
    attempt['status'] = 'fetched'
    entries.append(result)
except Exception as error:
    attempt.update(status='blocked',error=str(error))
    if isinstance(error, HTTPError):
        attempt['http_status'] = error.code
        attempt['final_url'] = error.url
entry['attempts'].append(attempt)
entry['retry_at'] = attempt['retrieved_at']
for e in entries:
    if 'resolved_url' in e:
        e['final_url'] = e.pop('resolved_url')
    if e['id'] == 'lec19-2021-nielsen.pdf':
        e['url'] = url
(root/'acquisition.json').write_text(json.dumps(entries,indent=2)+'\n')
(root/'retry-result.json').write_text(json.dumps(attempt,indent=2)+'\n')
print(json.dumps(attempt,indent=2))
