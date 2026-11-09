"""Minimal local content/source checks; not a Paxos implementation test."""
import hashlib
import json
import re
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
COURSE = ROOT.parent
fragment = json.loads((HERE / "manifest-fragment.json").read_text())
original = {s["id"]: s for s in json.loads((ROOT / "manifest.json").read_text())["sources"]}
seen = set()
for source in fragment["sources"]:
    assert source["id"].startswith("p8-paxos-") and source["id"] not in seen
    seen.add(source["id"])
    for field in ("url", "file", "sha256", "retrieved_at", "last_modified", "status", "scope", "license", "read_pages", "visual_pages"):
        assert field in source, (source["id"], field)
    assert hashlib.sha256((ROOT / source["file"]).read_bytes()).hexdigest() == source["sha256"]
    assert set(source["visual_pages"]) <= set(source["read_pages"])
    if "original_source_id" in source:
        for field in ("url", "file", "sha256", "retrieved_at", "last_modified"):
            assert source[field] == original[source["original_source_id"]][field]
faq = next(s for s in fragment["sources"] if s["id"] == "p8-paxos-faq")
response = json.loads((HERE / "faq-response.json").read_text())
for field in ("url", "final_url", "file", "sha256", "retrieved_at", "last_modified"):
    assert faq[field] == response[field]

detail = json.loads((COURSE / "course.json").read_text())
lecture_ids = {item["id"] for item in detail["lectures"]}
folder = COURSE / "lectures" / "update-paxos"
assert {p.name for p in folder.glob("*.md")} == {"notes.zh.md", "materials.zh.md"}
for path in sorted(folder.glob("*.md")):
    text = path.read_text()
    assert text.startswith("---\n") and "## 引用与来源" in text
    assert text.count("<details>") == text.count("</details>")
    assert text.count("$$") % 2 == 0
    assert all(line == line.rstrip() for line in text.splitlines()), path
    for lecture, view in re.findall(r"#/c/mit-6\.824-2021/lec/([^?\s)]+)\?v=(notes|materials|draft)", text):
        assert lecture in lecture_ids, lecture
        assert (COURSE / "lectures" / lecture / f"{view}.zh.md").is_file(), (lecture, view)
    print("checked", path.relative_to(COURSE))
print(f"checked {len(seen)} source hashes, original snapshot metadata, FAQ response metadata and local lecture routes")
