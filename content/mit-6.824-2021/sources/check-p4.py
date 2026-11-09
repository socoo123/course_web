"""Local P4 content checks; requires locally retained source snapshots.

Checks structure and provenance, not translation quality, audio, or lab correctness.
"""
import hashlib
import json
import re
import xml.etree.ElementTree as ET
from pathlib import Path

root = Path(__file__).resolve().parent.parent
sources = root / "sources"
course = json.loads((root / "course.json").read_text())
state = json.loads((root / "status.json").read_text())
lectures = {x["id"]: x for x in course["lectures"]}
labs = {x["id"]: x for x in course["labs"]}
for name in ["manifest-2021.json", "version-map-2021.json", "lab-code-manifest.json"]:
    json.loads((sources / name).read_text())

documents = [root / "lectures/lec09" / f"{kind}.zh.md"
             for kind in ["notes", "draft", "materials"]]
documents += [root / "lectures/update-lab-bridge/notes.zh.md"]
documents += [root / "labs/kvraft" / f"{kind}.zh.md" for kind in ["lab", "guide"]]
for path in documents:
    text = path.read_text()
    assert text.startswith("---\n") and "\nstatus:" in text, path
    assert len(re.findall(r"^```", text, re.M)) % 2 == 0, path
    for image in re.findall(r"!\[[^\]]*\]\(([^)]+)\)", text):
        assert (path.parent / image).is_file(), (path, image)
    for kind, ident, view in re.findall(
        r"#/c/mit-6\.824-2021/(lec|lab)/([^?\s)]+)\?v=(\w+)", text
    ):
        assert ident in (lectures if kind == "lec" else labs), (path, ident)
        target = root / ("lectures" if kind == "lec" else "labs") / ident
        filename = {"zh": "lab", "guide": "guide"}.get(view, view)
        assert (target / f"{filename}.zh.md").is_file(), (path, target, view)
for name in ["lec09", "update-lab-bridge"]:
    for path in (root / "lectures" / name / "assets").glob("*.svg"):
        ET.parse(path)

manifest = json.loads((sources / "manifest-2021.json").read_text())
records = list(manifest["sources"])
p4_records = []
for fragment in manifest["source_fragments"]:
    data = json.loads((sources / fragment).read_text())
    fragment_records = data["sources"] if "sources" in data else [data]
    if "sources" in data:
        fragment_records = fragment_records + data.get("derived_files", [])
    records.extend(fragment_records)
    if fragment.startswith("p4-"):
        p4_records.extend(fragment_records)
source_ids = [item["id"] for item in records if "id" in item]
assert len(set(source_ids)) == len(source_ids)
for record in p4_records:
    for item in [record] + record.get("derived_files", []):
        if isinstance(item, str):
            assert (sources / item).is_file(), item
        elif item.get("file") and item.get("sha256"):
            assert hashlib.sha256((sources / item["file"]).read_bytes()).hexdigest() == item["sha256"], item["file"]

def seconds(stamp):
    result = 0
    for part in stamp.split(":"):
        result = result * 60 + int(part)
    return result

draft = (root / "lectures/lec09/draft.zh.md").read_text()
segments = [(seconds(a), seconds(b)) for a, b in re.findall(
    r"^##\s+(\d+(?::\d{2}){1,2})[–—-](\d+(?::\d{2}){1,2})", draft, re.M)]
duration = seconds(lectures["lec09"]["video"]["duration"])
assert segments and segments[0][0] == 0 and segments[-1][1] == duration
assert all(a < b for a, b in segments)
assert all(segments[i-1][1] == segments[i][0] for i in range(1, len(segments)))
caption_files = list((sources / "p4-lec09").rglob("captions.normalized.json"))
assert len(caption_files) == 1
cues = json.loads(caption_files[0].read_text())
assert all(c["end_ms"] >= c["start_ms"] >= 0 for c in cues)
assert all(cues[i-1]["start_ms"] <= cues[i]["start_ms"] for i in range(1, len(cues)))
assert all(sum(a * 1000 <= c["start_ms"] < b * 1000 for a, b in segments) == 1 for c in cues)
metadata = [json.loads(p.read_text()) for p in (sources / "p4-lec09").glob("*metadata.json")]
assert len(metadata) == 1
assert metadata[0]["duration"] == duration
assert metadata[0]["id"] in lectures["lec09"]["video"]["youtube"]
assert state["versions"]["labCodeCommit"] == "513cac0aef010750fc74688da8a395974a83cf7a"
assert state["labTests"] == "not_run"
assert state["artifacts"]["lectureDocumentsCompleted"] == len(list(root.glob("lectures/*/*.zh.md")))
assert state["artifacts"]["labDocumentsCompleted"] == len(list(root.glob("labs/*/*.zh.md")))
assert state["artifacts"]["lectureIllustrationsCompleted"] == len(list(root.glob("lectures/*/assets/*.svg")))
assert state["content"]["lectures"]["update-lab-bridge"]["migration"] == "not_started_P5"
print("L9:", len(cues), "cues;", len(segments), "sections;", duration, "seconds;",
      cues[0]["start_ms"], "first ms;", max(c["end_ms"] for c in cues), "last end ms")
print("PASS: 6 P4 documents, JSON, source hashes, routes, images, SVG, fences, caption structure, totals")
