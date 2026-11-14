"""P2 content/provenance checks only; no assignment execution or network calls."""
import hashlib
import json
import re
from pathlib import Path
from urllib.parse import unquote
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parent.parent
SOURCES = ROOT / "sources"


def load(path):
    return json.loads(path.read_text())


course = load(ROOT / "course.json")
lectures = {x["id"]: x for x in course["lectures"]}
labs = {x["id"]: x for x in course["labs"]}
expected = {f"lectures/{x}/notes.zh.md" for x in [
    "lec01", "lec02", "bridge04", "bridge02", "bridge01", "bridge05", "bridge07", "bridge08"
]}
expected |= {"lectures/lec01/draft.zh.md", "lectures/lec02/draft.zh.md", "labs/a1-basics/guide.zh.md"}
actual = {str(p.relative_to(ROOT)) for folder in ["lectures", "labs"] for p in (ROOT / folder).rglob("*.md")}
assert actual == expected, {"missing": sorted(expected - actual), "out_of_P2": sorted(actual - expected)}
assert not list(SOURCES.rglob("*.md")), "Source Markdown would be published"
links = images = time_ranges = 0
svgs = set()

def seconds(text):
    result = 0
    for value in text.split(":"):
        result = result * 60 + float(value)
    return result


for relative in sorted(expected | {"resources.zh.md"}):
    path = ROOT / relative
    text = path.read_text()
    assert text.startswith("---\n"), relative
    for kind, target in re.findall(r"#/c/stanford-cs336-2026/(lec|lab)/([^?\s)#]+)", text):
        assert target in (lectures if kind == "lec" else labs), (relative, target)
        links += 1
    for target in re.findall(r"!\[[^\]]*\]\(([^)]+)\)", text):
        if target.startswith(("https://", "http://", "data:")):
            continue
        image = path.parent / unquote(target.split("#")[0])
        assert image.is_file(), (relative, target)
        images += 1
        if image.suffix == ".svg":
            svgs.add(image)
    if path.parent.name in {"lec01", "lec02"}:
        limit = seconds(lectures[path.parent.name]["video"]["duration"])
        for start, end in re.findall(r"\b((?:\d+:)?\d{1,2}:\d{2}(?:\.\d{1,3})?)\s*[–—]\s*((?:\d+:)?\d{1,2}:\d{2}(?:\.\d{1,3})?)\b", text):
            assert 0 <= seconds(start) <= seconds(end) <= limit, (relative, start, end)
            time_ranges += 1
for path in svgs:
    svg = ET.parse(path).getroot()
    assert svg.tag.endswith("svg")
    assert any(e.tag.endswith("title") for e in svg.iter()), path
    assert any(e.tag.endswith("desc") for e in svg.iter()), path
    assert not any(e.tag.endswith(("script", "foreignObject")) for e in svg.iter()), path
    for e in svg.iter():
        assert not any(k.endswith("href") and v.startswith(("http:", "https:")) for k, v in e.attrib.items()), path

checked = set()
source_records = 0
fragments = sorted(SOURCES.glob("p2-*/manifest-fragment.json"))
assert len(fragments) == 5, fragments
for path in fragments:
    data = load(path)
    records = data["sources"]
    ids = [x["id"] for x in records]
    assert len(ids) == len(set(ids)), path
    source_records += len(records)
    for record in records:
        for key in ["id", "url", "version", "license", "read_scope", "file", "sha256"]:
            assert key in record, (path, record.get("id"), key)
        file, digest = record["file"], record["sha256"]
        if file is None:
            assert digest is None
            continue
        source = SOURCES / file
        assert source.is_file(), (path, file)
        assert hashlib.sha256(source.read_bytes()).hexdigest() == digest, (path, file)
        checked.add((file, digest))

caption_results = []
for lecture, video_id, duration, cue_count in [
    ("lec01", "JuoVZkPBiKk", 4762, 1509), ("lec02", "kuYAsz7zspQ", 4645, 1425)
]:
    video = lectures[lecture]["video"]
    assert video["youtube"] == f"https://www.youtube.com/watch?v={video_id}"
    assert seconds(video["duration"]) == duration
    raw = load(SOURCES / f"p1-videos/captions/{video_id}.en-US.manual.json3")
    cues = [e for e in raw["events"] if e.get("segs")]
    assert len(cues) == cue_count
    previous_start = -1
    for cue in cues:
        start = cue["tStartMs"] / 1000
        end = start + cue["dDurationMs"] / 1000
        assert previous_start <= start <= end <= duration
        previous_start = start
    caption_results.append({"lecture": lecture, "cues": len(cues), "duration_seconds": duration})
    timing = load(SOURCES / f"p2-{lecture}/time-intervals.json")
    if lecture == "lec01":
        segments = [(b["start_seconds"] * 1000, b["end_seconds"] * 1000,
                     b["cue_indices_1_based_by_start"]) for b in timing["blocks"]]
        recorded_gaps = [(round(g["start_seconds"] * 1000), round(g["end_seconds"] * 1000))
                         for g in timing["caption_gaps"] if g["kind"] == "internal"]
    else:
        segments = [(b["start_ms"], b["end_ms"], [b["first_cue"], b["last_cue"]])
                    for b in timing["navigation_segments"]]
        recorded_gaps = [(g["start_ms"], g["end_ms"]) for g in timing["internal_gaps_gt_2s"]]
    covered = []
    previous_end = None
    for start, end, indices in segments:
        assert 0 <= start < end <= duration * 1000
        assert previous_end is None or abs(start - previous_end) < 0.01
        previous_end = end
        members = [i for i, cue in enumerate(cues, 1) if start - 0.01 <= cue["tStartMs"] < end - 0.01]
        assert members == ([] if indices is None else list(range(indices[0], indices[1] + 1)))
        covered.extend(members)
    assert covered == list(range(1, cue_count + 1))
    actual_gaps = []
    end = cues[0]["tStartMs"] + cues[0]["dDurationMs"]
    for cue in cues[1:]:
        start = cue["tStartMs"]
        if start - end > 2000:
            actual_gaps.append((end, start))
        end = max(end, start + cue["dDurationMs"])
    assert actual_gaps == recorded_gaps, (lecture, actual_gaps, recorded_gaps)

preflight = load(SOURCES / "p2-model-preflight.json")
assert preflight["resolvedSubagentModel"] == "openai-codex/gpt-6-astra"
assert preflight["resolvedSubagentEffort"] == "xhigh"
assert preflight["resolvedModelIsFallback"] is False
assert len(preflight["runtimeEvidence"]) == preflight["subagentsStarted"] == 5
readings = load(SOURCES / "reading-map.json")["readings"]
assert len(readings) == 16
assert all(r["materialFile"] == f'lectures/{r["home"]}/materials.zh.md' for r in readings)
tasks = load(SOURCES / "p2-a1/task-index.json")["tasks"]
assert len(tasks) == len({task["id"] for task in tasks}) == 38
source_tasks = re.findall(r"Problem \(([^)]+)\):", (SOURCES / "p1-assignments-a1-a4/a1/cs336_assignment1_basics.txt").read_text())
assert {task["id"] for task in tasks} == set(source_tasks)
print(json.dumps({
    "status": "passed", "phase": "P2", "lecture_documents": 10, "lab_documents": 1,
    "internal_links": links, "local_image_references": images, "parsed_svgs": len(svgs),
    "in_bounds_time_ranges": time_ranges, "source_fragments": len(fragments),
    "source_records": source_records, "verified_source_file_hashes": len(checked),
    "captions": caption_results, "paper_homes_unchanged_count": len(readings),
    "scope": "Content/provenance checks; not audio verification, full-paper reading or assignment execution"
}, ensure_ascii=False, indent=2))
