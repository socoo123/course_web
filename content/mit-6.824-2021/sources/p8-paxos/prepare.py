"""Verify reused snapshots, archive FAQ response metadata, extract/render PDF.

Run from any directory. This script never promotes fetched sources to reviewed.
"""
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from urllib.request import urlopen

import fitz

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
manifest = json.loads((ROOT / "manifest.json").read_text())
records = manifest["sources"]
ids = ["lec04-notes-1-2026", "lec04-notes-2-2026",
       "lec04-reading-4-2026", "home-2026", "schedule-2026"]
verified = []
for source_id in ids:
    record = next(item for item in records if item["id"] == source_id)
    actual = hashlib.sha256((ROOT / record["file"]).read_bytes()).hexdigest()
    assert actual == record["sha256"], source_id
    verified.append({"original_source_id": source_id, "sha256": actual})
    print("verified", source_id, actual)
(HERE / "hash-verification.json").write_text(json.dumps(verified, indent=2) + "\n")

faq_path = HERE / "paxos-faq.txt"
if not faq_path.exists():
    url = "https://pdos.csail.mit.edu/6.824/papers/paxos-faq.txt"
    with urlopen(url, timeout=60) as response:
        data = response.read()
        metadata = {
            "url": url, "final_url": response.geturl(),
            "retrieved_at": datetime.now(timezone.utc).isoformat(),
            "last_modified": response.headers.get("Last-Modified"),
            "http_status": response.status,
            "file": "p8-paxos/paxos-faq.txt",
            "sha256": hashlib.sha256(data).hexdigest(), "status": "fetched",
        }
    faq_path.write_bytes(data)
    (HERE / "faq-response.json").write_text(json.dumps(metadata, indent=2) + "\n")

document = fitz.open(ROOT / "update-2026-paxos-simple.pdf")
text = []
(HERE / "rendered").mkdir(exist_ok=True)
for number, page in enumerate(document, 1):
    text.append(f"\n=== PDF PAGE {number} ===\n" + page.get_text())
    page.get_pixmap(matrix=fitz.Matrix(1.3, 1.3)).save(HERE / "rendered" / f"page-{number:02}.png")
(HERE / "paxos-simple-extracted.txt").write_text("".join(text))
print("extracted and rendered", len(document), "pages")
