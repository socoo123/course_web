"""Verify P7 authored-content provenance and navigation; never execute course code."""
import hashlib
import json
import re
import xml.etree.ElementTree as ET
from pathlib import Path
from urllib.parse import parse_qs, unquote

ROOT = Path(__file__).resolve().parent.parent
SOURCES = ROOT / "sources"
VIDEOS = [("lec15", "2oH6PWPrYFo", 4794), ("lec16", "dIFAi87Ws4E", 4550), ("lec17", "26FtD08ZpOU", 4659)]
BODIES = [f"lectures/{lecture}/{kind}.zh.md" for lecture, _, _ in VIDEOS for kind in ("notes", "draft", "materials")]
BODIES += [f"lectures/{entry}/notes.zh.md" for entry in ("ext14", "ext15")]
BODIES += [f"labs/{entry}/{kind}.zh.md" for entry in ("a5-reasoning", "a5-safety-optional") for kind in ("lab", "guide")]
FRAGMENTS = ["lec15", "lec16", "lec17", "rl-papers", "mm-papers", "a5-reasoning", "a5-safety"]


def load(path):
    return json.loads(path.read_text())


def seconds(value):
    result = 0
    for part in value.split(":"):
        result = result * 60 + float(part)
    return result


def official_tasks(path):
    text = path.read_text()
    headers = list(re.finditer(r"Problem \(([^)]+)\):", text))
    result = {}
    for index, header in enumerate(headers):
        end = headers[index + 1].start() if index + 1 < len(headers) else text.index("Bibliography", header.end())
        block = text[header.end():end]
        point = re.search(r"\(([\d.]+)\s+points?\)", block)
        assert point and point.start() < 240, header[1]
        letters = re.findall(r"^\s*\(([a-z])\)", block[point.end():], re.M)
        result[header[1]] = {"points": float(point[1]), "letters": letters}
    return result


course = load(ROOT / "course.json")
lectures = {item["id"]: item for item in course["lectures"]}
labs = {item["id"]: item for item in course["labs"]}
links = image_refs = time_ranges = 0
svgs = set()
for relative in BODIES + ["resources.zh.md"]:
    path = ROOT / relative
    text = path.read_text()
    assert text.startswith("---\n"), relative
    for target in re.findall(r"(?<!!)\[[^\]]*\]\(([^)]+)\)", text):
        assert target.startswith(("https:", "http:")) or not re.search(r"\.md(?:[#?]|$)", target), (relative, "use HashRouter links", target)
        if target.startswith("#/c/stanford-cs336-2026/"):
            assert re.match(r"#/c/stanford-cs336-2026/(?:lec|lab)/", target), (relative, target)
    for kind, target, query in re.findall(r"#/c/stanford-cs336-2026/(lec|lab)/([^?\s)#]+)(?:\?([^\s)#]+))?", text):
        assert target in (lectures if kind == "lec" else labs), (relative, target)
        view = parse_qs(query).get("v", [None])[0]
        assert view in ({None, "notes", "draft", "materials"} if kind == "lec" else {None, "zh", "guide"}), (relative, view)
        links += 1
    for target in re.findall(r"!\[[^\]]*\]\(([^)]+)\)", text):
        assert not target.startswith(("http:", "https:", "data:")), (relative, target)
        image = path.parent / unquote(target.split("#")[0])
        assert image.is_file(), (relative, target)
        image_refs += 1
        if image.suffix == ".svg":
            svgs.add(image)
    if path.parent.name in {v[0] for v in VIDEOS} and path.name != "materials.zh.md":
        duration = seconds(lectures[path.parent.name]["video"]["duration"])
        for begin, end in re.findall(r"\b((?:\d+:)?\d{1,2}:\d{2}(?:\.\d{1,3})?)\s*[–—]\s*((?:\d+:)?\d{1,2}:\d{2}(?:\.\d{1,3})?)\b", text):
            assert 0 <= seconds(begin) <= seconds(end) <= duration, (relative, begin, end)
            time_ranges += 1
for image in svgs:
    root = ET.parse(image).getroot()
    assert root.tag.endswith("svg")
    assert any(node.tag.endswith("title") for node in root.iter()), image
    assert any(node.tag.endswith("desc") for node in root.iter()), image
    for node in root.iter():
        assert not node.tag.endswith(("script", "foreignObject")), image
        assert not any(key.endswith("href") and value.startswith(("http:", "https:")) for key, value in node.attrib.items()), image

source_ids, verified_hashes = set(), set()
source_count = 0
for name in FRAGMENTS:
    fragment_path = SOURCES / f"p7-{name}/manifest-fragment.json"
    fragment = load(fragment_path)
    for record in fragment["sources"]:
        assert record["id"] not in source_ids, record["id"]
        source_ids.add(record["id"])
        for field in ("id", "kind", "url", "status", "file", "sha256", "version", "retrieved_at", "license", "read_scope", "read_at", "chinese_treatment", "material_files"):
            assert field in record, (fragment_path, record.get("id"), field)
        source_count += 1
        file, digest = record["file"], record["sha256"]
        if file is None:
            assert digest is None, record["id"]
            continue
        source = SOURCES / file
        assert source.is_file(), (fragment_path, file)
        if (file, digest) not in verified_hashes:
            assert hashlib.sha256(source.read_bytes()).hexdigest() == digest, (fragment_path, file)
            verified_hashes.add((file, digest))
    assert not list((SOURCES / f"p7-{name}").rglob("*.md")), name

caption_results = []
for lecture, video_id, duration in VIDEOS:
    video = lectures[lecture]["video"]
    assert video["youtube"] == f"https://www.youtube.com/watch?v={video_id}"
    assert seconds(video["duration"]) == duration
    cues = [cue for cue in load(SOURCES / f"p1-videos/captions/{video_id}.en-US.manual.json3")["events"] if cue.get("segs")]
    previous = -1
    for cue in cues:
        start, end = cue["tStartMs"], cue["tStartMs"] + cue["dDurationMs"]
        assert previous <= start <= end <= duration * 1000, lecture
        previous = start
    timing = load(SOURCES / f"p7-{lecture}/time-intervals.json")
    covered, previous_end = [], 0
    blocks = timing["intervals"] if lecture == "lec17" else timing["blocks"]
    for block in blocks:
        start, end = round(block["start_seconds"] * 1000), round(block["end_seconds"] * 1000)
        assert start == previous_end and 0 <= start < end <= duration * 1000, (lecture, block)
        previous_end = end
        members = [i for i, cue in enumerate(cues, 1) if start <= cue["tStartMs"] < end]
        if lecture == "lec17":
            indices = None if block["cue_first"] is None else [block["cue_first"], block["cue_last"]]
        else:
            indices = block["cue_indices_1_based_by_start"]
        assert members == ([] if indices is None else list(range(indices[0], indices[1] + 1))), (lecture, block)
        covered.extend(members)
    assert previous_end == duration * 1000 and covered == list(range(1, len(cues) + 1)), lecture
    gaps, end = [], cues[0]["tStartMs"] + cues[0]["dDurationMs"]
    for cue in cues[1:]:
        if cue["tStartMs"] - end > 2000:
            gaps.append((end, cue["tStartMs"]))
        end = max(end, cue["tStartMs"] + cue["dDurationMs"])
    recorded = [(round(g["start_seconds"] * 1000), round(g["end_seconds"] * 1000)) for g in timing["internal_gaps_over_two_seconds"]]
    assert recorded == gaps, (lecture, recorded, gaps)
    caption_results.append({"lecture": lecture, "cues": len(cues), "duration_seconds": duration, "internal_gaps_over_2s": len(gaps)})

preflight = load(SOURCES / "p7-model-preflight.json")
assert preflight["resolvedSubagentModel"] == "openai-codex/gpt-6-astra"
assert preflight["resolvedSubagentEffort"] == "xhigh" and preflight["resolvedModelIsFallback"] is False
assert len(preflight["runtimeEvidence"]) == preflight["subagentsStarted"] == 7
readings = load(SOURCES / "reading-map.json")["readings"]
assert len(readings) == 16
assert all(r["materialFile"] == f'lectures/{r["home"]}/materials.zh.md' for r in readings)
for paper, home in [("paper12", "lec15"), ("paper13", "lec16"), ("paper14", "lec16"), ("paper15", "lec17"), ("paper16", "lec17")]:
    assert next(r for r in readings if r["id"] == paper)["home"] == home
assignment_results = []
for lab, source, folder, count, points, letter_count in [("a5-reasoning", "main-2026.txt", "a5-reasoning", 28, 90, 11), ("a5-safety-optional", "optional-safety-2026.txt", "a5-safety", 16, 61, 42)]:
    tasks = official_tasks(SOURCES / "p1-assignment-a5/raw" / source)
    assert len(tasks) == count and sum(t["points"] for t in tasks.values()) == points
    assert sum(len(t["letters"]) for t in tasks.values()) == letter_count
    assert {t["id"] for t in labs[lab]["tasks"]} == set(tasks), lab
    coverage = load(SOURCES / f"p7-{folder}/task-coverage.json")
    id_key = "id" if lab == "a5-safety-optional" else "official_id"
    subquestion_key = "subparts" if lab == "a5-safety-optional" else "subquestions"
    mapped = {t[id_key]: t for t in coverage["tasks"]}
    assert set(mapped) == set(tasks), lab
    for task_id, task in tasks.items():
        assert mapped[task_id]["points"] == task["points"], (lab, task_id)
        assert [q["letter"] for q in mapped[task_id][subquestion_key] if q["letter"] is not None] == task["letters"], (lab, task_id)
    assignment_results.append({"lab": lab, "tasks": count, "points": points, "lettered_subquestions": letter_count})

print(json.dumps({"phase": "P7", "status": "passed", "body_documents": len(BODIES), "internal_links": links, "local_image_references": image_refs, "parsed_svgs": len(svgs), "in_bounds_time_ranges": time_ranges, "source_fragments": len(FRAGMENTS), "source_records": source_count, "verified_unique_source_hashes": len(verified_hashes), "captions": caption_results, "paper_homes_preserved": len(readings), "assignments": assignment_results, "scope": "Structural/provenance/timing evidence only; independent source and technical review recorded separately. No official assignment execution."}, ensure_ascii=False, indent=2))
