"""Minimal local evidence and content checks; no git, build, or proof execution."""
import hashlib
import json
import re
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
COURSE = ROOT.parent
fragment = json.loads((HERE / "manifest-fragment.json").read_text())
original = {s["id"]: s for s in json.loads((ROOT / "manifest.json").read_text())["sources"]}
required = {"id", "url", "file", "sha256", "retrieved_at", "last_modified", "status", "scope", "license", "read_pages", "visual_pages"}
seen = set()
for source in fragment["sources"]:
    assert required <= source.keys()
    assert source["id"].startswith("p8-verification-")
    assert source["id"] not in seen
    seen.add(source["id"])
    assert hashlib.sha256((ROOT / source["file"]).read_bytes()).hexdigest() == source["sha256"]
    old = original[source["original_source_id"]]
    for field in ("sha256", "retrieved_at", "last_modified"):
        assert source[field] == old[field], (source["id"], field)
paper = next(s for s in fragment["sources"] if s["id"] == "p8-verification-paper")
assert paper["read_pages"] == paper["visual_pages"] == list(range(1, 18))
assert all((HERE / "pages" / f"{p:02d}.png").is_file() for p in paper["visual_pages"])
for item in fragment.get("derived_files", []):
    assert hashlib.sha256((ROOT / item["file"]).read_bytes()).hexdigest() == item["sha256"]

metadata = json.loads((COURSE / "course.json").read_text())
ids = {"lec": {x["id"] for x in metadata["lectures"]}, "lab": {x["id"] for x in metadata["labs"]}}
for name in ("notes.zh.md", "materials.zh.md"):
    path = COURSE / "lectures" / "update-verification" / name
    text = path.read_text()
    assert text.startswith("---\n")
    assert "## 引用与来源" in text
    assert text.count("<details>") == text.count("</details>")
    assert text.count("$$") % 2 == 0
    assert text.count("```") % 2 == 0
    assert not any(line.rstrip() != line for line in text.splitlines())
    for kind, item in re.findall(r"#/c/mit-6\.824-2021/(lec|lab)/([^?\s)]+)", text):
        assert item in ids[kind], (path, kind, item)
    for image in re.findall(r"!\[[^\]]*\]\(([^)]+)\)", text):
        assert (path.parent / image).is_file()
    print(name, len(text.splitlines()), "lines: metadata, routes, markup OK")
assert not (COURSE / "lectures" / "update-verification" / "draft.zh.md").exists()
print("4 reused-source hashes and original timestamps match; 17 read/visual pages recorded; no proof or lab execution")
