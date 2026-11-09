"""Verify reused snapshots and retain text/page renders for local reading."""
import hashlib
import json
from pathlib import Path
import subprocess

import fitz

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
manifest = json.loads((ROOT / "manifest.json").read_text())
ids = {"lec15-notes-1-2026", "lec15-reading-2-2026", "home-2026", "schedule-2026"}
for item in manifest["sources"]:
    if item["id"] in ids:
        digest = hashlib.sha256((ROOT / item["file"]).read_bytes()).hexdigest()
        assert digest == item["sha256"], item["id"]
        print(item["id"], digest, item["retrieved_at"], item.get("last_modified"))

doc = fitz.open(ROOT / "update-2026-ironfleet.pdf")
(HERE / "pages").mkdir(exist_ok=True)
text = []
for number, page in enumerate(doc, 1):
    text.append(f"\n=== PDF PAGE {number} ===\n" + page.get_text(sort=True))
    page.get_pixmap(matrix=fitz.Matrix(1.5, 1.5)).save(HERE / "pages" / f"{number:02d}.png")
(HERE / "ironfleet-text.txt").write_text("".join(text))
subprocess.run([
    "pdftotext", "-layout", str(ROOT / "update-2026-ironfleet.pdf"),
    str(HERE / "ironfleet-layout.txt"),
], check=True)
print("PDF pages:", len(doc))
