"""Acquire only the new FAQ; preserve reused source provenance unchanged."""
import hashlib
import json
import subprocess
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent

manifest = json.loads((ROOT / "manifest.json").read_text())
for source in manifest["sources"]:
    if source["id"] in {"lec18-notes-1-2026", "lec18-reading-2-2026"}:
        actual = hashlib.sha256((ROOT / source["file"]).read_bytes()).hexdigest()
        assert actual == source["sha256"], source["id"]
        print(source["id"], actual, source["retrieved_at"])

target = HERE / "ray-faq.txt"
if not target.exists():
    url = "https://pdos.csail.mit.edu/6.824/papers/ray-faq.txt"
    with urllib.request.urlopen(url, timeout=60) as response:
        data = response.read()
        record = {
            "url": url,
            "final_url": response.url,
            "retrieved_at": datetime.now(timezone.utc).isoformat(),
            "http_status": response.status,
            "last_modified": response.headers.get("Last-Modified"),
            "content_type": response.headers.get("Content-Type"),
            "etag": response.headers.get("ETag"),
            "response_date": response.headers.get("Date"),
            "file": "p9-ray/ray-faq.txt",
            "sha256": hashlib.sha256(data).hexdigest(),
            "bytes": len(data),
            "status": "fetched",
        }
    target.write_bytes(data)
    (HERE / "acquisition.json").write_text(json.dumps(record, indent=2) + "\n")
print((HERE / "acquisition.json").read_text())
subprocess.run(["pdftoppm", "-f", "16", "-l", "16", "-scale-to", "1900", "-png", "-singlefile", str(ROOT / "update-2026-ray.pdf"), str(HERE / "page-16")], check=True)
subprocess.run(["pdfinfo", str(ROOT / "update-2026-ray.pdf")], check=True)
