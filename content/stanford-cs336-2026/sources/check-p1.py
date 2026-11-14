"""P1-only structural/source checks; does not execute course code or access paid services."""
import hashlib
import json
import pathlib
import re
from urllib.parse import urlparse

ROOT = pathlib.Path(__file__).resolve().parent.parent
SOURCES = ROOT / "sources"

def load(path):
    return json.loads(path.read_text())

course = load(ROOT / "course.json")
manifest = load(SOURCES / "manifest.json")
readings = load(SOURCES / "reading-map.json")["readings"]
status = load(ROOT / "status.json")
lectures = {entry["id"]: entry for entry in course["lectures"]}
labs = {entry["id"]: entry for entry in course["labs"]}
assert len(lectures) == len(course["lectures"]) == 43
assert len(labs) == len(course["labs"]) == 7
assert all(f"lec{n:02d}" in lectures for n in range(1, 20))
assert len(readings) == len({entry["id"] for entry in readings}) == 16
assert not list(SOURCES.rglob("*.md")), "Source Markdown would be published"
assert not list((ROOT / "lectures").rglob("*.md")), "P1 must not create lecture bodies"
assert not list((ROOT / "labs").rglob("*.md")), "P1 must not create lab bodies"
assert status["artifacts"]["lectureDocumentsWritten"] == 0
assert status["artifacts"]["labDocumentsWritten"] == 0
assert status["batches"]["P2"] == "not_started"
assert status["nextStage"]["autoStart"] is False

ids = [item["id"] for item in manifest["sources"]]
assert len(ids) == len(set(ids)), "Duplicate manifest source ids"
checked = set()

def check_files(value):
    if isinstance(value, dict):
        file, digest = value.get("file"), value.get("sha256")
        if isinstance(file, str) and isinstance(digest, str) and re.fullmatch(r"[0-9a-f]{64}", digest):
            path = SOURCES / file
            assert path.is_file(), f"Missing local source: {file}"
            if (file, digest) not in checked:
                assert hashlib.sha256(path.read_bytes()).hexdigest() == digest, f"Hash mismatch: {file}"
                checked.add((file, digest))
        for child in value.values():
            check_files(child)
    elif isinstance(value, list):
        for child in value:
            check_files(child)

check_files(manifest)
for fragment in manifest["source_fragments"]:
    path = SOURCES / fragment
    assert path.is_file(), fragment
    check_files(load(path))

for item in readings:
    assert item["home"] in lectures
    assert item["materialFile"] == f'lectures/{item["home"]}/materials.zh.md'
    assert item["requirement"] != "pending_P1"
    assert item["version"] and item["verifiedScope"]
    assert item["chineseTreatment"] and item["license"]
    assert all(x in lectures or x in {r["id"] for r in readings} for x in item["prerequisites"])
    assert all(x in labs for x in item["relatedAssignments"])

links = 0
for path in ROOT.glob("*.md"):
    for match in re.finditer(r"#\/c\/stanford-cs336-2026(?:\/(lec|lab)\/([^?\s)#]+))?", path.read_text()):
        kind, target = match.groups()
        if kind:
            assert target in (lectures if kind == "lec" else labs), (path, target)
        links += 1

videos = []
for key, entry in lectures.items():
    if "video" not in entry:
        continue
    video = entry["video"]
    assert re.fullmatch(r"(?:\d+:)?\d{1,2}:\d{2}", video["duration"]), (key, video)
    assert video.get("youtube") or video.get("bilibili")
    assert not video.get("bilibili"), "No official Bilibili chain collected for CS336"
    assert urlparse(video["youtube"]).hostname in {"www.youtube.com", "youtube.com", "youtu.be"}
    videos.append(key)
assert len(videos) == status["artifacts"]["verifiedLectureVideoHeaders"]
preflight = load(SOURCES / "model-preflight.json")
assert preflight["resolvedSubagentModel"] == "openai-codex/gpt-6-astra"
assert preflight["resolvedSubagentEffort"] == "xhigh"
assert len(preflight["runtimeEvidence"]) == preflight["subagentsStarted"]
print(json.dumps({"status":"passed","lecture_entries":len(lectures),"lab_entries":len(labs),"paper_placements":len(readings),"manifest_sources":len(ids),"verified_file_hashes":len(checked),"internal_links":links,"video_headers":videos,"lecture_bodies":0,"lab_bodies":0,"experiments":"not_run"}, ensure_ascii=False, indent=2))
