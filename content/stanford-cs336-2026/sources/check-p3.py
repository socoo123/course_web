"""P3 publication checks: content, source identity and navigation; no assignment runs."""
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


def seconds(value):
    total = 0
    for part in value.split(":"):
        total = 60 * total + float(part)
    return total


course = load(ROOT / "course.json")
lectures = {entry["id"]: entry for entry in course["lectures"]}
labs = {entry["id"]: entry for entry in course["labs"]}
body_files = [f"lectures/{name}/notes.zh.md" for name in
              ["lec03", "lec04", "bridge03", "bridge06", "ext01", "ext02", "ext03"]]
body_files += ["lectures/lec03/draft.zh.md", "lectures/lec04/draft.zh.md",
               "lectures/lec03/materials.zh.md", "labs/a1-basics/lab.zh.md",
               "labs/a1-basics/guide.zh.md"]
assert not list(SOURCES.rglob("*.md")), "Source Markdown would be bundled publicly"
assert not (ROOT / "lectures/lec04/materials.zh.md").exists(), "No duplicate reading home"
links = images = time_ranges = 0
svgs = set()
for relative in body_files + ["resources.zh.md"]:
    path = ROOT / relative
    text = path.read_text()
    assert text.startswith("---\n"), relative
    assert "#/c/stanford-cs336-2026/resources" not in text, (relative, "Resources use the course root route")
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
    if path.parent.name in {"lec03", "lec04"}:
        limit = seconds(lectures[path.parent.name]["video"]["duration"])
        for start, end in re.findall(r"\b((?:\d+:)?\d{1,2}:\d{2}(?:\.\d{1,3})?)\s*[–—]\s*((?:\d+:)?\d{1,2}:\d{2}(?:\.\d{1,3})?)\b", text):
            assert 0 <= seconds(start) <= seconds(end) <= limit, (relative, start, end)
            time_ranges += 1
for path in svgs:
    svg = ET.parse(path).getroot()
    assert svg.tag.endswith("svg"), path
    assert any(element.tag.endswith("title") for element in svg.iter()), path
    assert any(element.tag.endswith("desc") for element in svg.iter()), path
    for element in svg.iter():
        assert not element.tag.endswith(("script", "foreignObject")), path
        assert not any(key.endswith("href") and value.startswith(("http:", "https:"))
                       for key, value in element.attrib.items()), path

checked = set()
source_records = 0
fragments = [SOURCES / f"p3-{name}/manifest-fragment.json" for name in
             ["lec03", "lec04", "bridges", "extensions", "papers", "a1"]]
for path in fragments:
    records = load(path)["sources"]
    assert len({record["id"] for record in records}) == len(records), path
    source_records += len(records)
    for record in records:
        for key in ["id", "kind", "url", "file", "sha256", "version", "retrieved_at",
                    "license", "read_scope", "read_at", "chinese_treatment", "material_files"]:
            assert key in record, (path, record.get("id"), key)
        file, digest = record["file"], record["sha256"]
        if file is None:
            assert digest is None
            continue
        source = SOURCES / file
        assert source.is_file(), (path, file)
        if (file, digest) not in checked:
            assert hashlib.sha256(source.read_bytes()).hexdigest() == digest, (path, file)
            checked.add((file, digest))

caption_results = []
for lecture, video_id, duration, count in [
    ("lec03", "lVynu4bo1rY", 5354, 2020), ("lec04", "cKSwj_qZ8Jg", 5180, 1938)
]:
    video = lectures[lecture]["video"]
    assert video["youtube"] == f"https://www.youtube.com/watch?v={video_id}"
    assert seconds(video["duration"]) == duration
    raw = load(SOURCES / f"p1-videos/captions/{video_id}.en-US.manual.json3")
    cues = [cue for cue in raw["events"] if cue.get("segs")]
    assert len(cues) == count
    previous = -1
    for cue in cues:
        start = cue["tStartMs"]
        end = start + cue["dDurationMs"]
        assert previous <= start <= end <= duration * 1000
        previous = start
    timing = load(SOURCES / f"p3-{lecture}/time-intervals.json")
    covered = []
    previous_end = 0
    for block in timing["blocks"]:
        start = round(block["start_seconds"] * 1000)
        end = round(block["end_seconds"] * 1000)
        assert start == previous_end and 0 <= start < end <= duration * 1000, (lecture, block)
        previous_end = end
        members = [index for index, cue in enumerate(cues, 1) if start <= cue["tStartMs"] < end]
        indices = block["cue_indices_1_based_by_start"]
        assert members == ([] if indices is None else list(range(indices[0], indices[1] + 1))), (lecture, block)
        covered.extend(members)
    assert previous_end == duration * 1000
    assert covered == list(range(1, count + 1)), lecture
    actual_gaps = []
    end = cues[0]["tStartMs"] + cues[0]["dDurationMs"]
    for cue in cues[1:]:
        start = cue["tStartMs"]
        if start - end > 2000:
            actual_gaps.append((end, start))
        end = max(end, start + cue["dDurationMs"])
    recorded = [(round(gap["start_seconds"] * 1000), round(gap["end_seconds"] * 1000))
                for gap in timing["caption_gaps"] if gap["kind"] == "internal"]
    assert recorded == actual_gaps, (lecture, recorded, actual_gaps)
    caption_results.append({"lecture": lecture, "cues": count, "duration_seconds": duration,
                            "internal_gaps_over_2s": len(actual_gaps)})

preflight = load(SOURCES / "p3-model-preflight.json")
assert preflight["resolvedSubagentModel"] == "openai-codex/gpt-6-astra"
assert preflight["resolvedSubagentEffort"] == "xhigh"
assert preflight["resolvedModelIsFallback"] is False
assert len(preflight["runtimeEvidence"]) == preflight["subagentsStarted"] == 6
readings = load(SOURCES / "reading-map.json")["readings"]
assert len(readings) == 16
assert all(item["materialFile"] == f'lectures/{item["home"]}/materials.zh.md' for item in readings)
assert all(item["home"] == "lec03" for item in readings[:2])
tasks = load(SOURCES / "p2-a1/task-index.json")["tasks"]
source_tasks = re.findall(r"Problem \(([^)]+)\):", (SOURCES / "p1-assignments-a1-a4/a1/cs336_assignment1_basics.txt").read_text())
assert len(tasks) == len({task["id"] for task in tasks}) == 38
assert {task["id"] for task in tasks} == set(source_tasks)
lab_text = (ROOT / "labs/a1-basics/lab.zh.md").read_text()
coverage = load(SOURCES / "p3-a1/task-coverage.json")
coverage_tasks = {task["id"]: task for task in coverage["tasks"]}
assert set(coverage_tasks) == set(source_tasks)
lettered_questions = 0
for task in tasks:
    assert task["id"] in lab_text, task["id"]
    mapped = coverage_tasks[task["id"]]
    assert mapped["points"] == task["points"], task["id"]
    assert mapped["lab_section"] in lab_text, task["id"]
    letters = set(task.get("subtasks", {}))
    mapped_letters = {item["id"] for item in mapped["coverage_items"] if re.fullmatch("[a-z]", item["id"])}
    assert letters == mapped_letters, (task["id"], letters, mapped_letters)
    lettered_questions += len(letters)
assert lettered_questions == coverage["declared_coverage"]["lettered_subquestions"] == 25
print(json.dumps({
    "status": "passed", "phase": "P3", "body_documents": len(body_files),
    "internal_links": links, "local_image_references": images, "parsed_svgs": len(svgs),
    "in_bounds_time_ranges": time_ranges, "source_fragments": len(fragments),
    "source_records": source_records, "verified_source_file_hashes": len(checked),
    "captions": caption_results, "paper_homes_preserved": len(readings),
    "a1_problem_ids": len(tasks), "a1_lettered_subquestions": lettered_questions,
    "scope": "Content/provenance and requirement-map validation; Main separately reviewed every task statement. No audio, assignment execution or full-paper reading is implied."
}, ensure_ascii=False, indent=2))
