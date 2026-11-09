"""P6 local provenance/structure checks, using retained source snapshots.

Time structure is not evidence of translation accuracy or audio/frame review.
"""
import hashlib
import json
import re
import xml.etree.ElementTree as ET
from pathlib import Path
from urllib.parse import urljoin

ROOT = Path(__file__).resolve().parent.parent
SOURCES = ROOT / "sources"
IDS = ["lec11", "lec12", "lec15", "lec17"]


def load(path):
    return json.loads(path.read_text())


def seconds(stamp):
    value = 0
    for part in stamp.split(":"):
        value = value * 60 + int(part)
    return value


def check_file(item):
    if isinstance(item, str):
        assert (SOURCES / item).is_file(), item
        return
    if item.get("file") and item.get("sha256"):
        path = SOURCES / item["file"]
        assert hashlib.sha256(path.read_bytes()).hexdigest() == item["sha256"], path
    for child in item.get("derived_files", []):
        check_file(child)


course = load(ROOT / "course.json")
state = load(ROOT / "status.json")
inventory = load(SOURCES / "schedule-inventory-2021.json")
mapping = load(SOURCES / "version-map-2021.json")
lectures = {x["id"]: x for x in course["lectures"]}
labs = {x["id"]: x for x in course["labs"]}
documents = [ROOT / "lectures" / ident / f"{kind}.zh.md"
             for ident in IDS for kind in ["notes", "draft", "materials"]]
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
        target = ROOT / ("lectures" if kind == "lec" else "labs") / ident
        filename = {"zh": "lab", "guide": "guide"}.get(view, view)
        assert (target / f"{filename}.zh.md").is_file(), (path, target, view)
for ident in IDS:
    for path in (ROOT / "lectures" / ident / "assets").glob("*.svg"):
        ET.parse(path)

manifest = load(SOURCES / "manifest-2021.json")
records = list(manifest["sources"])
for fragment in manifest["source_fragments"]:
    data = load(SOURCES / fragment)
    entries = data["sources"] + data.get("derived_files", []) if "sources" in data else [data]
    records.extend(entries)
    if fragment.startswith("p6-"):
        for record in entries:
            check_file(record)
source_ids = [x["id"] for x in records if isinstance(x, dict) and "id" in x]
assert len(source_ids) == len(set(source_ids)), "duplicate source IDs"
for ident in IDS:
    entry = next(x for x in inventory["lectures"] if x["id"] == ident)
    fragment = f"p6-{ident}/manifest-fragment.json"
    assert fragment in manifest["source_fragments"], ident
    sources = load(SOURCES / fragment)["sources"]
    for link in entry.get("notes", []) + entry.get("readings", []) + entry.get("faq", []):
        url = urljoin(inventory["url_base"], link)
        matches = [s for s in sources if s.get("url") == url]
        assert matches and any(s["status"] == "reviewed" for s in matches), (ident, url)
assert "faq" not in next(x for x in inventory["lectures"] if x["id"] == "lec11")
assert "update-chain-replication" not in lectures
assert len(lectures) == 29 and len(labs) == 5

# The integration record explicitly pairs each independent video with its cues.
for ident in IDS:
    text = (ROOT / "lectures" / ident / "draft.zh.md").read_text()
    sections = [(seconds(a), seconds(b)) for a, b in re.findall(
        r"^#{2,3}\s+(\d+(?::\d{2}){1,2})[–—-](\d+(?::\d{2}){1,2})", text, re.M)]
    timelines = []
    for section in sections:
        if section[0] == 0:
            timelines.append([])
        assert timelines, (ident, "first timeline must begin at zero")
        timelines[-1].append(section)
    videos = state["p6Captions"][ident]["videos"]
    scheduled = next(x for x in inventory["lectures"] if x["id"] == ident)["videos"]
    assert len(timelines) == len(videos) == len(scheduled), ident
    for index, (segments, video) in enumerate(zip(timelines, videos)):
        duration = video["durationSeconds"]
        assert segments[-1][1] == duration, (ident, index)
        assert all(a < b for a, b in segments), (ident, index)
        assert all(segments[i - 1][1] == segments[i][0]
                   for i in range(1, len(segments))), (ident, index)
        cues = load(ROOT / video["normalizedCaptions"])
        metadata = load(ROOT / video["metadata"])
        assert metadata["id"] == video["videoId"] and metadata["duration"] == duration
        assert video["videoId"] in scheduled[index], (ident, index)
        assert all(metadata.get(key) for key in ["title", "channel", "upload_date", "license"])
        assert len(cues) == video["cues"] and len(segments) == video["draftSections"]
        assert all(c["end_ms"] >= c["start_ms"] >= 0 for c in cues), ident
        assert all(cues[i - 1]["start_ms"] <= cues[i]["start_ms"]
                   for i in range(1, len(cues))), ident
        assert all(sum(a * 1000 <= c["start_ms"] < b * 1000 for a, b in segments) == 1
                   for c in cues), (ident, index)
        assert cues[0]["start_ms"] == video["firstStartMs"]
        assert max(c["end_ms"] for c in cues) == video["lastEndMs"]
        if index == 0:
            assert seconds(lectures[ident]["video"]["duration"]) == duration
            assert video["videoId"] in lectures[ident]["video"]["youtube"]
        print(ident, index + 1, video["videoId"], len(cues), "cues",
              len(segments), "sections", duration, "seconds")

assert state["versions"]["labCodeCommit"] == mapping["lab_commit"] == "513cac0aef010750fc74688da8a395974a83cf7a"
assert state["labTests"] == "not_run"
assert state["artifacts"]["lectureDocumentsCompleted"] == len(list(ROOT.glob("lectures/*/*.zh.md")))
assert state["artifacts"]["labDocumentsCompleted"] == len(list(ROOT.glob("labs/*/*.zh.md")))
assert state["artifacts"]["lectureIllustrationsCompleted"] == len(list(ROOT.glob("lectures/*/assets/*.svg")))
assert len(state["p6Captions"]["lec15"]["videos"]) == 2
assert state["content"]["lectures"]["lec06"]["draft"] == "no_video_listed"
assert state["content"]["lectures"]["lec08"]["draft"] == "no_video_listed"
print("PASS: 12 P6 documents, source hashes, JSON, routes, images, SVG, fences, five independent timelines and totals")
