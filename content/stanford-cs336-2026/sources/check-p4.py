"""Validate P4 content/provenance/navigation only; never execute official assignments."""
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
    result = 0
    for part in value.split(":"):
        result = result * 60 + float(part)
    return result


course = load(ROOT / "course.json")
lectures = {item["id"]: item for item in course["lectures"]}
labs = {item["id"]: item for item in course["labs"]}
lecture_ids = [f"lec{n:02}" for n in range(5, 9)]
extension_ids = [f"ext{n:02}" for n in range(4, 10)]
body_files = [f"lectures/{entry}/{kind}.zh.md" for entry in lecture_ids for kind in ("notes", "draft")]
body_files += [f"lectures/{entry}/notes.zh.md" for entry in extension_ids]
body_files += ["lectures/lec06/materials.zh.md", "lectures/lec08/materials.zh.md",
               "labs/a2-systems/lab.zh.md", "labs/a2-systems/guide.zh.md"]
links = images = time_ranges = 0
svgs = set()
for relative in body_files + ["resources.zh.md"]:
    path = ROOT / relative
    text = path.read_text()
    assert text.startswith("---\n"), relative
    assert "#/c/stanford-cs336-2026/resources" not in text, relative
    for kind, target in re.findall(r"#/c/stanford-cs336-2026/(lec|lab)/([^?\s)#]+)", text):
        assert target in (lectures if kind == "lec" else labs), (relative, target)
        links += 1
    for target in re.findall(r"!\[[^\]]*\]\(([^)]+)\)", text):
        assert not target.startswith(("https://", "http://", "data:")), (relative, target)
        image = path.parent / unquote(target.split("#")[0])
        assert image.is_file(), (relative, target)
        images += 1
        if image.suffix == ".svg":
            svgs.add(image)
    if path.parent.name in lecture_ids and path.name != "materials.zh.md":
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
        assert not any(key.endswith("href") and value.startswith(("http:", "https:"))
                       for key, value in node.attrib.items()), image

fragment_names = [*lecture_ids, "attention-profiling", "distributed", "papers", "a2"]
verified_hashes = set()
source_count = 0
for name in fragment_names:
    path = SOURCES / f"p4-{name}/manifest-fragment.json"
    records = load(path)["sources"]
    assert len(records) == len({record["id"] for record in records}), path
    source_count += len(records)
    for record in records:
        for field in ["id", "kind", "url", "file", "sha256", "version", "retrieved_at",
                      "license", "read_scope", "read_at", "chinese_treatment", "material_files"]:
            assert field in record, (path, record.get("id"), field)
        file, digest = record["file"], record["sha256"]
        if file is None:
            assert digest is None, record["id"]
            continue
        source = SOURCES / file
        assert source.is_file(), (path, file)
        if (file, digest) not in verified_hashes:
            assert hashlib.sha256(source.read_bytes()).hexdigest() == digest, (path, file)
            verified_hashes.add((file, digest))
    assert not list((SOURCES / f"p4-{name}").rglob("*.md")), name

caption_results = []
for lecture, video_id, duration in [
    ("lec05", "izZba4UA7iY", 4719), ("lec06", "xnDHaNUvHBg", 5201),
    ("lec07", "SzpOcwdIL0Y", 4862), ("lec08", "6-cXp-aOmdg", 4810)
]:
    video = lectures[lecture]["video"]
    assert video["youtube"] == f"https://www.youtube.com/watch?v={video_id}", lecture
    assert seconds(video["duration"]) == duration, lecture
    raw = load(SOURCES / f"p1-videos/captions/{video_id}.en-US.manual.json3")
    cues = [cue for cue in raw["events"] if cue.get("segs")]
    last_start = -1
    for cue in cues:
        start = cue["tStartMs"]
        end = start + cue["dDurationMs"]
        assert last_start <= start <= end <= duration * 1000, lecture
        last_start = start
    timing = load(SOURCES / f"p4-{lecture}/time-intervals.json")
    covered = []
    last_end = 0
    for block in timing["blocks"]:
        start = round(block["start_seconds"] * 1000)
        end = round(block["end_seconds"] * 1000)
        assert start == last_end and 0 <= start < end <= duration * 1000, (lecture, block)
        last_end = end
        members = [i for i, cue in enumerate(cues, 1) if start <= cue["tStartMs"] < end]
        indices = block["cue_indices_1_based_by_start"]
        assert members == ([] if indices is None else list(range(indices[0], indices[1] + 1))), (lecture, block)
        covered.extend(members)
    assert last_end == duration * 1000 and covered == list(range(1, len(cues) + 1)), lecture
    gaps = []
    end = cues[0]["tStartMs"] + cues[0]["dDurationMs"]
    for cue in cues[1:]:
        if cue["tStartMs"] - end > 2000:
            gaps.append((end, cue["tStartMs"]))
        end = max(end, cue["tStartMs"] + cue["dDurationMs"])
    recorded = [(round(gap["start_seconds"] * 1000), round(gap["end_seconds"] * 1000))
                for gap in timing["caption_gaps"] if gap["kind"] == "internal"]
    assert recorded == gaps, (lecture, recorded, gaps)
    caption_results.append({"lecture": lecture, "cues": len(cues), "duration_seconds": duration,
                            "internal_gaps_over_2s": len(gaps)})

preflight = load(SOURCES / "p4-model-preflight.json")
assert preflight["resolvedSubagentModel"] == "openai-codex/gpt-6-astra"
assert preflight["resolvedSubagentEffort"] == "xhigh" and preflight["resolvedModelIsFallback"] is False
assert len(preflight["runtimeEvidence"]) == preflight["subagentsStarted"] == 6
assert len(preflight["resumption"]["runtimeEvidence"]) == 6
assert {item["agent"] for item in preflight["resumption"]["runtimeEvidence"]} == {
    item["agent"] for item in preflight["runtimeEvidence"]
}
assert preflight["resumption"]["modelChangedOrSubstituted"] is False
readings = load(SOURCES / "reading-map.json")["readings"]
assert len(readings) == 16
assert all(item["materialFile"] == f'lectures/{item["home"]}/materials.zh.md' for item in readings)
for paper, home in [("paper03", "lec06"), ("paper04", "lec06"), ("paper05", "lec08")]:
    assert next(item for item in readings if item["id"] == paper)["home"] == home

source_text = (SOURCES / "p1-assignments-a1-a4/a2/cs336_assignment2_systems.txt").read_text()
source_problems = list(re.finditer(r"Problem \(([^)]+)\):([\s\S]*?)\((\d+)\s+points?\)", source_text))
coverage = load(SOURCES / "p4-a2/task-coverage.json")
mapped = {task["id"]: task for task in coverage["tasks"]}
assert set(mapped) == {match[1] for match in source_problems}
lab_text = (ROOT / "labs/a2-systems/lab.zh.md").read_text()
letters_total = 0
roman_total = 0
for i, match in enumerate(source_problems):
    task = mapped[match[1]]
    end = source_problems[i + 1].start() if i + 1 < len(source_problems) else len(source_text)
    section = source_text[match.end():end]
    labels = re.findall(r"^\s*\(([a-z]+)\)\s", section, re.M)
    nested = set()
    for position in range(len(labels) - 1):
        if labels[position:position + 2] != ["i", "ii"]:
            continue
        for offset, roman in enumerate(("i", "ii", "iii", "iv", "v", "vi", "vii", "viii", "ix", "x")):
            index = position + offset
            if index >= len(labels) or labels[index] != roman:
                break
            nested.add(index)
    letters = {label for index, label in enumerate(labels) if len(label) == 1 and index not in nested}
    roman_items = {labels[index] for index in nested}
    mapped_roman = {item["id"].split(".")[-1] for item in task["coverage_items"]
                    if re.fullmatch(r"[a-z]\.[ivx]+", item["id"])}
    assert roman_items == mapped_roman, (match[1], roman_items, mapped_roman)
    roman_total += len(roman_items)
    assert task["points"] == int(match[3]), match[1]
    assert task["lab_section"] in lab_text, (match[1], task["lab_section"])
    assert match[1] in lab_text, match[1]
    mapped_letters = {item["id"] for item in task["coverage_items"] if re.fullmatch("[a-z]", item["id"])}
    assert letters == mapped_letters, (match[1], letters, mapped_letters)
    letters_total += len(letters)

print(json.dumps({
    "phase": "P4", "status": "passed", "body_documents": len(body_files),
    "internal_links": links, "local_image_references": images, "parsed_svgs": len(svgs),
    "in_bounds_time_ranges": time_ranges, "source_fragments": len(fragment_names),
    "source_records": source_count, "verified_unique_source_hashes": len(verified_hashes),
    "captions": caption_results, "paper_homes_preserved": len(readings),
    "a2_scored_tasks": len(source_problems), "a2_lettered_subquestions": letters_total,
    "a2_nested_roman_subitems": roman_total,
    "scope": "Content/provenance/requirements navigation. Not audio verification, full-paper reading or official assignment execution."
}, ensure_ascii=False, indent=2))
