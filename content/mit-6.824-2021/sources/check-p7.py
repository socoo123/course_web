"""P7 provenance, routes, caption structure and integration checks.

Run against retained local snapshots. Structure is not audio/frame verification.
"""
import hashlib
import json
import re
import xml.etree.ElementTree as ET
from pathlib import Path
from urllib.parse import urljoin

ROOT = Path(__file__).resolve().parent.parent
SOURCES = ROOT / "sources"
IDS = ["lec16", "lec18", "lec19", "lec20"]


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
for path in documents + [ROOT / "resources.zh.md"]:
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
        filename = {"zh": "lab", "guide": "guide"}.get(view, view)
        target = ROOT / ("lectures" if kind == "lec" else "labs") / ident / f"{filename}.zh.md"
        if not target.is_file():
            # Public navigation deliberately exposes registered future topics.
            assert kind == "lec" and state["content"]["lectures"][ident][view] == "not_started", (path, target)
for path in ROOT.glob("lectures/*/assets/*.svg"):
    ET.parse(path)

manifest = load(SOURCES / "manifest-2021.json")
records = list(manifest["sources"])
for fragment in manifest["source_fragments"]:
    data = load(SOURCES / fragment)
    entries = data["sources"] + data.get("derived_files", []) if "sources" in data else [data]
    records.extend(entries)
    if fragment.startswith("p7-"):
        for record in entries:
            check_file(record)
source_ids = [x["id"] for x in records if isinstance(x, dict) and "id" in x]
assert len(source_ids) == len(set(source_ids)), "duplicate source IDs"
for ident in IDS:
    entry = next(x for x in inventory["lectures"] if x["id"] == ident)
    fragment = f"p7-{ident}/manifest-fragment.json"
    assert fragment in manifest["source_fragments"], ident
    sources = load(SOURCES / fragment)["sources"]
    for link in entry.get("notes", []) + entry.get("readings", []) + entry.get("faq", []):
        url = urljoin(inventory["url_base"], link)
        matches = [s for s in sources if s.get("url") == url]
        assert matches, (ident, url)
        assert any(s["status"] in {"reviewed", "partial", "blocked"} for s in matches), (ident, url)
assert "update-sundr" not in lectures and "update-chain-replication" not in lectures
assert len(lectures) == 29 and len(labs) == 5

total_cues = total_sections = 0
for ident in IDS:
    text = (ROOT / "lectures" / ident / "draft.zh.md").read_text()
    segments = [(seconds(a), seconds(b)) for a, b in re.findall(
        r"^#{2,3}\s+(\d+(?::\d{2}){1,2})[–—-](\d+(?::\d{2}){1,2})", text, re.M)]
    videos = state["p7Captions"][ident]["videos"]
    scheduled = next(x for x in inventory["lectures"] if x["id"] == ident)["videos"]
    assert len(videos) == len(scheduled) == 1, ident
    video = videos[0]
    fragment_video = load(SOURCES / f"p7-{ident}/manifest-fragment.json")["videos"][0]
    duration = video["durationSeconds"]
    assert segments[0][0] == 0 and segments[-1][1] == duration, ident
    assert all(a < b for a, b in segments), ident
    assert all(segments[i - 1][1] == segments[i][0] for i in range(1, len(segments))), ident
    cues = load(ROOT / video["normalizedCaptions"])
    metadata = load(ROOT / video["metadata"])
    assert fragment_video["metadata"] == metadata, ident
    assert "sources/" + fragment_video["metadata_file"] == video["metadata"], ident
    assert "sources/" + fragment_video["normalized_caption_file"] == video["normalizedCaptions"], ident
    assert fragment_video["draft_segment_count"] == len(segments), ident
    assert metadata["id"] == video["videoId"] and metadata["duration"] == duration
    assert video["videoId"] in scheduled[0], ident
    assert all(metadata.get(key) for key in ["title", "channel", "upload_date", "license"])
    assert set(metadata) <= {"id", "title", "duration", "channel", "channel_id", "uploader", "upload_date", "license", "webpage_url"}
    assert len(cues) == video["cues"] and len(segments) == video["draftSections"]
    assert all(c["end_ms"] >= c["start_ms"] >= 0 for c in cues), ident
    assert all(cues[i - 1]["start_ms"] <= cues[i]["start_ms"] for i in range(1, len(cues))), ident
    assert all(sum(a * 1000 <= c["start_ms"] < b * 1000 for a, b in segments) == 1 for c in cues), ident
    assert cues[0]["start_ms"] == video["firstStartMs"]
    assert max(c["end_ms"] for c in cues) == video["lastEndMs"]
    assert seconds(lectures[ident]["video"]["duration"]) == duration
    assert video["videoId"] in lectures[ident]["video"]["youtube"]
    total_cues += len(cues)
    total_sections += len(segments)
    print(ident, video["videoId"], len(cues), "cues", len(segments), "sections", duration,
          "seconds; raw end overrun(ms)", max(0, video["lastEndMs"] - duration * 1000))

assert state["versions"]["labCodeCommit"] == mapping["lab_commit"] == "513cac0aef010750fc74688da8a395974a83cf7a"
assert state["labTests"] == "not_run" and state["learnerLabCompletion"] == "not_tracked"
assert state["artifacts"]["lectureDocumentsCompleted"] == len(list(ROOT.glob("lectures/*/*.zh.md")))
assert state["artifacts"]["labDocumentsCompleted"] == len(list(ROOT.glob("labs/*/*.zh.md")))
assert state["artifacts"]["lectureIllustrationsCompleted"] == len(list(ROOT.glob("lectures/*/assets/*.svg")))
assert len(state["p6Captions"]["lec15"]["videos"]) == 2
for ident in ["lec06", "lec08"]:
    assert state["content"]["lectures"][ident]["draft"] == "no_video_listed"
for ident in ["update-paxos", "update-go-patterns", "update-verification", "update-lambda", "update-ray", "update-bft", "lec21"]:
    assert state["content"]["lectures"][ident]["notes"] == "not_started"
assert inventory["lectures"][17]["reading_scope"] == "until Section 3.4"
print("PASS: 12 P7 documents, shared navigation, source hashes, JSON, routes, images, SVG, metadata and totals;",
      total_cues, "cues /", total_sections, "sections. No audio/frame or lab verification claimed.")
