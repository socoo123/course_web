"""Validate P6 provenance/navigation/timing; never execute course assignment code."""
import hashlib
import json
import re
import xml.etree.ElementTree as ET
from pathlib import Path
from urllib.parse import parse_qs, unquote

ROOT = Path(__file__).resolve().parent.parent
SOURCES = ROOT / "sources"


def load(path):
    return json.loads(path.read_text())


def seconds(value):
    result = 0
    for part in value.split(":"):
        result = result * 60 + float(part)
    return result


course = load(ROOT / "course.json")
lectures = {item["id"]: item for item in course["lectures"]}
labs = {item["id"]: item for item in course["labs"]}
videos = [("lec13", "-qm0ln33G24", 4921), ("lec14", "5sxHosTLPF8", 5086)]
bodies = [f"lectures/{entry}/{kind}.zh.md" for entry, _, _ in videos for kind in ("notes", "draft")]
bodies += ["lectures/lec14/materials.zh.md", "lectures/ext13/notes.zh.md", "labs/a4-data/lab.zh.md", "labs/a4-data/guide.zh.md"]
links = image_references = time_ranges = 0
svgs = set()
for relative in bodies + ["resources.zh.md"]:
    path = ROOT / relative
    text = path.read_text()
    assert text.startswith("---\n"), relative
    for kind, target, query in re.findall(r"#/c/stanford-cs336-2026/(lec|lab)/([^?\s)#]+)(?:\?([^\s)#]+))?", text):
        assert target in (lectures if kind == "lec" else labs), (relative, target)
        view = parse_qs(query).get("v", [None])[0]
        assert view in ({None, "notes", "draft", "materials"} if kind == "lec" else {None, "zh", "guide"}), (relative, view)
        links += 1
    for target in re.findall(r"!\[[^\]]*\]\(([^)]+)\)", text):
        assert not target.startswith(("http:", "https:", "data:")), (relative, target)
        image = path.parent / unquote(target.split("#")[0])
        assert image.is_file(), (relative, target)
        image_references += 1
        if image.suffix == ".svg":
            svgs.add(image)
    if path.parent.name in ("lec13", "lec14") and path.name != "materials.zh.md":
        duration = seconds(lectures[path.parent.name]["video"]["duration"])
        for begin, end in re.findall(r"\b((?:\d+:)?\d{1,2}:\d{2}(?:\.\d{1,3})?)\s*[–—]\s*((?:\d+:)?\d{1,2}:\d{2}(?:\.\d{1,3})?)\b", text):
            assert 0 <= seconds(begin) <= seconds(end) <= duration, (relative, begin, end)
            time_ranges += 1
for image in svgs:
    root = ET.parse(image).getroot()
    assert root.tag.endswith("svg"), image
    assert any(node.tag.endswith("title") for node in root.iter()), image
    assert any(node.tag.endswith("desc") for node in root.iter()), image
    for node in root.iter():
        assert not node.tag.endswith(("script", "foreignObject")), image
        assert not any(key.endswith("href") and value.startswith(("http:", "https:")) for key, value in node.attrib.items()), image

fragment_names = ["lec13", "lec14", "papers", "audit", "a4"]
verified_hashes = set()
source_ids = set()
source_count = 0
for name in fragment_names:
    fragment = SOURCES / f"p6-{name}/manifest-fragment.json"
    for record in load(fragment)["sources"]:
        assert record["id"] not in source_ids, record["id"]
        source_ids.add(record["id"])
        for field in ("id", "kind", "url", "file", "sha256", "version", "retrieved_at", "license", "read_scope", "read_at", "chinese_treatment", "material_files"):
            assert field in record, (fragment, record.get("id"), field)
        source_count += 1
        file, digest = record["file"], record["sha256"]
        if file is None:
            assert digest is None, record["id"]
            continue
        source = SOURCES / file
        assert source.is_file(), (fragment, file)
        if (file, digest) not in verified_hashes:
            assert hashlib.sha256(source.read_bytes()).hexdigest() == digest, (fragment, file)
            verified_hashes.add((file, digest))
    assert not list((SOURCES / f"p6-{name}").rglob("*.md")), name

caption_results = []
for lecture, video_id, duration in videos:
    video = lectures[lecture]["video"]
    assert video["youtube"] == f"https://www.youtube.com/watch?v={video_id}", lecture
    assert seconds(video["duration"]) == duration, lecture
    raw = load(SOURCES / f"p1-videos/captions/{video_id}.en-US.manual.json3")
    cues = [cue for cue in raw["events"] if cue.get("segs")]
    previous = -1
    for cue in cues:
        start, end = cue["tStartMs"], cue["tStartMs"] + cue["dDurationMs"]
        assert previous <= start <= end <= duration * 1000, lecture
        previous = start
    timing = load(SOURCES / f"p6-{lecture}/time-intervals.json")
    if lecture == "lec13":
        blocks = [
            {"start_seconds": segment["start_ms"] / 1000,
             "end_seconds": segment["end_ms"] / 1000,
             "cue_indices_1_based_by_start": None if segment["first_cue"] is None else [segment["first_cue"], segment["last_cue"]]}
            for segment in timing["segments"]
        ]
        recorded = [(gap["start_ms"], gap["end_ms"]) for gap in timing["internal_gaps_gt_2s"]]
    else:
        blocks = timing["blocks"]
        recorded = [(round(gap["start_seconds"] * 1000), round(gap["end_seconds"] * 1000))
                    for gap in timing["internal_gaps_over_two_seconds"]]
    covered, previous_end = [], 0
    for block in blocks:
        start, end = round(block["start_seconds"] * 1000), round(block["end_seconds"] * 1000)
        assert start == previous_end and 0 <= start < end <= duration * 1000, (lecture, block)
        previous_end = end
        members = [i for i, cue in enumerate(cues, 1) if start <= cue["tStartMs"] < end]
        indices = block["cue_indices_1_based_by_start"]
        assert members == ([] if indices is None else list(range(indices[0], indices[1] + 1))), (lecture, block)
        covered.extend(members)
    assert previous_end == duration * 1000 and covered == list(range(1, len(cues) + 1)), lecture
    gaps, end = [], cues[0]["tStartMs"] + cues[0]["dDurationMs"]
    for cue in cues[1:]:
        if cue["tStartMs"] - end > 2000:
            gaps.append((end, cue["tStartMs"]))
        end = max(end, cue["tStartMs"] + cue["dDurationMs"])
    assert recorded == gaps, (lecture, recorded, gaps)
    caption_results.append({"lecture": lecture, "cues": len(cues), "duration_seconds": duration, "internal_gaps_over_2s": len(gaps)})

preflight = load(SOURCES / "p6-model-preflight.json")
assert preflight["resolvedSubagentModel"] == "openai-codex/gpt-6-astra"
assert preflight["resolvedSubagentEffort"] == "xhigh" and preflight["resolvedModelIsFallback"] is False
assert len(preflight["runtimeEvidence"]) == preflight["subagentsStarted"] == 5
readings = load(SOURCES / "reading-map.json")["readings"]
assert len(readings) == 16
assert all(item["materialFile"] == f'lectures/{item["home"]}/materials.zh.md' for item in readings)
assert all(next(item for item in readings if item["id"] == paper)["home"] == "lec14" for paper in ("paper08", "paper09"))
assert not (ROOT / "lectures/lec13/materials.zh.md").exists()
assert not (ROOT / "lectures/ext13/draft.zh.md").exists()
source_text = (SOURCES / "p1-assignments-a1-a4/a4/cs336_assignment4_data.txt").read_text()
problems = re.findall(r"Problem \(([^)]+)\):[^\n]*\((\d+) points\)", source_text)
assert len(problems) == 13 and sum(int(points) for _, points in problems) == 71
assert {task["id"] for task in labs["a4-data"]["tasks"]} == set(dict(problems))
coverage = load(SOURCES / "p6-a4/task-coverage.json")
assert {task["official_id"]: task["points"] for task in coverage["tasks"]} == {key: int(points) for key, points in problems}
assert sum(question["letter"] is not None for task in coverage["tasks"] for question in task["subquestions"]) == 27

print(json.dumps({"phase": "P6", "status": "passed", "body_documents": len(bodies), "internal_links": links, "local_image_references": image_references, "parsed_svgs": len(svgs), "in_bounds_time_ranges": time_ranges, "source_fragments": len(fragment_names), "source_records": source_count, "verified_unique_source_hashes": len(verified_hashes), "captions": caption_results, "paper_homes_preserved": len(readings), "a4_source_tasks": len(problems), "a4_source_points": 71, "scope": "Provenance, navigation and cue coverage only. Requirement fidelity and technical claims reviewed by Main against originals; no audio, official code or training execution."}, ensure_ascii=False, indent=2))
