"""Verify reused snapshots and render targeted pages; never refetch sources."""
import hashlib
import json
from pathlib import Path

import fitz

HERE = Path(__file__).resolve().parent
SOURCES = HERE.parent
manifest = json.loads((SOURCES / "manifest.json").read_text())
ids = ["lec17-notes-1-2026", "lec17-reading-2-2026", "schedule-2026"]
for source in manifest["sources"]:
    if source["id"] in ids:
        actual = hashlib.sha256((SOURCES / source["file"]).read_bytes()).hexdigest()
        assert actual == source["sha256"], source["id"]
        print(source["id"], actual, "MATCH")

for name, filename, pages in [
    ("slides", "update-2026-mbrooker_cs_slides_2026.pdf", [31, 49, 50, 51, 52, 53, 54, 55, 57]),
    ("paper", "update-2026-atc23-brooker.pdf", [6]),
]:
    doc = fitz.open(SOURCES / filename)
    out = HERE / "pages" / name
    out.mkdir(parents=True, exist_ok=True)
    for page in pages:
        doc[page - 1].get_pixmap(matrix=fitz.Matrix(1.5, 1.5)).save(out / f"{page:02}.png")
    print(name, "PDF pages", len(doc), "targeted renders", pages)
