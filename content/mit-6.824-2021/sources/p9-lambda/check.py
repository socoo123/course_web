"""Minimal local checks; no build, git, network or shared-file writes."""
import hashlib
import json
import re
from pathlib import Path

import fitz

HERE = Path(__file__).resolve().parent
SOURCES = HERE.parent
COURSE = SOURCES.parent
fragment = json.loads((HERE / "manifest-fragment.json").read_text())
originals = {
    item["id"]: item
    for item in json.loads((SOURCES / "manifest.json").read_text())["sources"]
}
ids = [s["id"] for s in fragment["sources"]]
assert len(ids) == len(set(ids))
assert all(i.startswith("p9-lambda-") for i in ids)
for source in fragment["sources"]:
    old = originals[source["original_source_id"]]
    for key in ["url", "file", "sha256", "retrieved_at", "last_modified", "final_url"]:
        if key in old:
            assert source.get(key) == old[key], (source["id"], key)
    if source["file"]:
        path = SOURCES / source["file"]
        assert hashlib.sha256(path.read_bytes()).hexdigest() == source["sha256"]
        if path.suffix == ".pdf":
            count = len(fitz.open(path))
            assert count == source["page_count"]
            assert source["read_pages"] == list(range(1, count + 1))
            assert set(source["visual_pages"]).issubset(source["read_pages"])

detail = json.loads((COURSE / "course.json").read_text())
lecture_ids = {lecture["id"] for lecture in detail["lectures"]}
for filename in ["notes.zh.md", "materials.zh.md"]:
    path = COURSE / "lectures" / "update-lambda" / filename
    text = path.read_text()
    assert text.startswith("---\n")
    assert text.count("```") % 2 == 0
    assert text.count("<details>") == text.count("</details>")
    assert text.count("$$") % 2 == 0
    assert all(line == line.rstrip() for line in text.splitlines())
    for lecture in re.findall(r"#/c/mit-6\.824-2021/lec/([^?)]+)", text):
        assert lecture in lecture_ids, lecture
    assert not re.search(r"!\[.*?\]\(", text), "No published image assets expected"
    print(filename, len(text.splitlines()), "lines", len(text), "characters")
assert not (COURSE / "lectures/update-lambda/draft.zh.md").exists()
for subdir, pages in [("slides", [31, 49, 50, 51, 52, 53, 54, 55, 57]), ("paper", [6])]:
    assert all((HERE / "pages" / subdir / f"{p:02}.png").is_file() for p in pages)
print("PASS: exact reused metadata/hashes, page scopes, source ids, routes and Markdown checks")
