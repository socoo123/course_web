"""One publisher-path variant and the DOI PDF entry discovered in search."""
import json
from concurrent.futures import ThreadPoolExecutor

from acquire import HERE, fetch

targets = [
    ('p8-go-cacm-canonical', 'https://cacm.acm.org/research/the-go-programming-language-and-environment', 'cacm-canonical.html'),
    ('p8-go-cacm-epdf', 'https://dl.acm.org/doi/epdf/10.1145/3488716', 'cacm-epdf.response'),
]

if __name__ == '__main__':
    with ThreadPoolExecutor(max_workers=2) as pool:
        records = list(pool.map(lambda args: fetch(*args), targets))
    (HERE / 'fetch-alternates.json').write_text(json.dumps(records, indent=2) + '\n')
    print(json.dumps(records, indent=2))
