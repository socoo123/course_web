"""Local P5 provenance/structure checks; requires retained source snapshots.

Does not establish translation accuracy, audio coverage, or lab correctness.
"""
import hashlib
import json
import re
import tarfile
import xml.etree.ElementTree as ET
from pathlib import Path

root = Path(__file__).resolve().parent.parent
sources = root / "sources"
course = json.loads((root / "course.json").read_text())
state = json.loads((root / "status.json").read_text())
lectures = {x["id"]: x for x in course["lectures"]}
labs = {x["id"]: x for x in course["labs"]}
for name in ["version-map-2021.json", "lab-code-manifest.json"]:
    json.loads((sources / name).read_text())

documents = [root / "lectures" / lec / f"{kind}.zh.md"
             for lec in ["lec13", "lec14"]
             for kind in ["notes", "draft", "materials"]]
documents += [root / "lectures/update-lab-bridge/notes.zh.md"]
documents += [root / "labs/shardkv" / f"{kind}.zh.md" for kind in ["lab", "guide"]]
for path in documents:
    text = path.read_text()
    assert text.startswith("---\n") and "\nstatus:" in text, path
    assert len(re.findall(r"^```", text, re.M)) % 2 == 0, path
    assert all(line.rstrip() == line for line in text.splitlines()), path
    for image in re.findall(r"!\[[^\]]*\]\(([^)]+)\)", text):
        assert (path.parent / image).is_file(), (path, image)
    for kind, ident, view in re.findall(
        r"#/c/mit-6\.824-2021/(lec|lab)/([^?\s)]+)\?v=(\w+)", text
    ):
        assert ident in (lectures if kind == "lec" else labs), (path, ident)
        target = root / ("lectures" if kind == "lec" else "labs") / ident
        filename = {"zh": "lab", "guide": "guide"}.get(view, view)
        assert (target / f"{filename}.zh.md").is_file(), (path, target, view)
for lec in ["lec13", "lec14", "update-lab-bridge"]:
    for path in (root / "lectures" / lec / "assets").glob("*.svg"):
        ET.parse(path)

manifest = json.loads((sources / "manifest-2021.json").read_text())
records = list(manifest["sources"])
p5_records = []
for fragment in manifest["source_fragments"]:
    data = json.loads((sources / fragment).read_text())
    entries = data["sources"] + data.get("derived_files", []) if "sources" in data else [data]
    records.extend(entries)
    if fragment.startswith("p5-"):
        p5_records.extend(entries)
ids = [x["id"] for x in records if isinstance(x, dict) and "id" in x]
assert len(ids) == len(set(ids)), "duplicate source IDs"

def check_file(item):
    if isinstance(item, str):
        assert (sources / item).is_file(), item
        return
    if item.get("file") and item.get("sha256"):
        assert hashlib.sha256((sources / item["file"]).read_bytes()).hexdigest() == item["sha256"], item["file"]
    for child in item.get("derived_files", []):
        check_file(child)

code_manifest = json.loads((sources / "lab-code-manifest.json").read_text())
with tarfile.open(sources / code_manifest["archive"]) as archive:
    for record in p5_records:
        check_file(record)
        for member in record.get("members", []):
            data = archive.extractfile("6.5840-golabs-2026/" + member["path"]).read()
            assert hashlib.sha256(data).hexdigest() == member["sha256"], member["path"]

def seconds(stamp):
    value = 0
    for part in stamp.split(":"):
        value = value * 60 + int(part)
    return value

for lec in ["lec13", "lec14"]:
    text = (root / "lectures" / lec / "draft.zh.md").read_text()
    segments = [(seconds(a), seconds(b)) for a, b in re.findall(
        r"^##\s+(\d+(?::\d{2}){1,2})[–—-](\d+(?::\d{2}){1,2})", text, re.M)]
    duration = seconds(lectures[lec]["video"]["duration"])
    assert segments and segments[0][0] == 0 and segments[-1][1] == duration, lec
    assert all(a < b for a, b in segments), lec
    assert all(segments[i-1][1] == segments[i][0] for i in range(1, len(segments))), lec
    captions = list((sources / f"p5-{lec}").rglob("captions.normalized.json"))
    assert len(captions) == 1, lec
    cues = json.loads(captions[0].read_text())
    assert all(c["end_ms"] >= c["start_ms"] >= 0 for c in cues), lec
    assert all(cues[i-1]["start_ms"] <= cues[i]["start_ms"] for i in range(1, len(cues))), lec
    assert all(sum(a*1000 <= c["start_ms"] < b*1000 for a, b in segments) == 1 for c in cues), lec
    metadata = [json.loads(p.read_text()) for p in (sources / f"p5-{lec}").glob("*metadata.json")]
    assert len(metadata) == 1 and metadata[0]["duration"] == duration, lec
    assert metadata[0]["id"] in lectures[lec]["video"]["youtube"], lec
    print(lec, len(cues), "cues", len(segments), "sections", duration, "seconds",
          "first_ms", cues[0]["start_ms"], "last_end_ms", max(c["end_ms"] for c in cues))

assert state["versions"]["labCodeCommit"] == "513cac0aef010750fc74688da8a395974a83cf7a"
assert state["labTests"] == "not_run"
assert state["artifacts"]["lectureDocumentsCompleted"] == len(list(root.glob("lectures/*/*.zh.md")))
assert state["artifacts"]["labDocumentsCompleted"] == len(list(root.glob("labs/*/*.zh.md")))
assert state["artifacts"]["lectureIllustrationsCompleted"] == len(list(root.glob("lectures/*/assets/*.svg")))
assert state["content"]["lectures"]["update-lab-bridge"]["migration"] == "complete_P5"
print("PASS: 9 P5 documents, JSON, source/member hashes, routes, images, SVG, fences, caption structure, totals")
