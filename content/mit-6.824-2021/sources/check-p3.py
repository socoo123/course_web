"""Local P3 integrity checks; requires the uncommitted source snapshots.

Does not validate translation, review audio/screens, or run labs.
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
for p in [root / "status.json", sources / "manifest-2021.json",
          sources / "version-map-2021.json", sources / "schedule-inventory-2021.json"]:
    json.loads(p.read_text())

documents = []
for name in ["lec03", "lec04", "lec05", "lec07"]:
    for kind in ["notes", "draft"] + (["materials"] if name != "lec07" else []):
        p = root / "lectures" / name / f"{kind}.zh.md"
        assert p.is_file(), p
        documents.append(p)
documents += [root / "labs/raft" / f"{kind}.zh.md" for kind in ["lab", "guide"]]
for p in documents:
    text = p.read_text()
    assert text.startswith("---\n") and "\nstatus:" in text, p
    assert len(re.findall(r"^```", text, re.M)) % 2 == 0, p
    for image in re.findall(r"!\[[^\]]*\]\(([^)]+)\)", text):
        assert (p.parent / image).is_file(), (p, image)
    for kind, ident, view in re.findall(
        r"#/c/mit-6\.824-2021/(lec|lab)/([^?\s)]+)\?v=(\w+)", text
    ):
        assert ident in (lectures if kind == "lec" else labs), (p, ident)
        target = root / ("lectures" if kind == "lec" else "labs") / ident
        filename = {"zh": "lab", "guide": "guide"}.get(view, view)
        assert (target / f"{filename}.zh.md").is_file(), (p, target, view)
for p in root.glob("lectures/lec0[3457]/assets/*.svg"):
    ET.parse(p)

manifest = json.loads((sources / "manifest-2021.json").read_text())
records = list(manifest["sources"])
for fragment in manifest.get("source_fragments", []):
    data = json.loads((sources / fragment).read_text())
    records.extend(data["sources"] if "sources" in data else [data])
    if "sources" in data:
        records.extend(data.get("derived_files", []))
assert len({s["id"] for s in records}) == len(records)
for s in records:
    for item in [s] + s.get("derived_files", []):
        if isinstance(item, str):
            assert (sources / item).is_file(), item
            continue
        if item.get("file") and item.get("sha256"):
            assert hashlib.sha256((sources / item["file"]).read_bytes()).hexdigest() == item["sha256"], item["file"]

def seconds(stamp):
    result = 0
    for part in stamp.split(":"):
        result = result * 60 + int(part)
    return result

for name in ["lec03", "lec04", "lec05", "lec07"]:
    p = root / "lectures" / name / "draft.zh.md"
    segments = [(seconds(a), seconds(b)) for a, b in re.findall(
        r"^##\s+(\d+(?::\d{2}){1,2})[–—-](\d+(?::\d{2}){1,2})", p.read_text(), re.M)]
    assert segments and segments[0][0] == 0, (name, segments)
    assert all(a < b for a, b in segments), name
    assert all(segments[i-1][1] == segments[i][0] for i in range(1, len(segments))), name
    duration = seconds(lectures[name]["video"]["duration"])
    metadata_name = "video.metadata.json" if name in ["lec03", "lec04"] else "metadata.json"
    metadata = json.loads((sources / f"p3-{name}" / metadata_name).read_text())
    assert metadata["duration"] == duration, name
    assert metadata["id"] in lectures[name]["video"]["youtube"], name
    assert segments[-1][1] == duration, (name, segments[-1], duration)
    caption_files = list((sources / f"p3-{name}").rglob("captions.normalized.json"))
    assert len(caption_files) == 1, (name, caption_files)
    cues = json.loads(caption_files[0].read_text())
    assert all(c["end_ms"] >= c["start_ms"] >= 0 for c in cues), name
    assert all(cues[i-1]["start_ms"] <= cues[i]["start_ms"] for i in range(1,len(cues))), name
    assert all(c["start_ms"] < duration*1000 for c in cues), name
    print(name, "cues", len(cues), "segments", len(segments), "first_ms", cues[0]["start_ms"],
          "last_end_ms", max(c["end_ms"] for c in cues), "duration", duration)

assert state["versions"]["labCodeCommit"] == "513cac0aef010750fc74688da8a395974a83cf7a"
assert state["labTests"] == "not_run"
assert state["artifacts"]["lectureDocumentsCompleted"] == len(list(root.glob("lectures/*/*.zh.md")))
assert state["artifacts"]["labDocumentsCompleted"] == len(list(root.glob("labs/*/*.zh.md")))
assert state["artifacts"]["lectureIllustrationsCompleted"] == len(list(root.glob("lectures/*/assets/*.svg")))
assert not (root / "lectures/lec07/materials.zh.md").exists()
print(f"PASS: {len(documents)} P3 documents, source hashes, JSON, routes, images, SVG, fences, caption structure")
