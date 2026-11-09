"""P9 source/content integration checks; local originals required; no experiments."""
import hashlib
import json
import re
import xml.etree.ElementTree as ET
from pathlib import Path
from urllib.parse import urljoin

ROOT = Path(__file__).resolve().parent.parent
SOURCES = ROOT / "sources"
TOPICS = {"update-lambda": "lambda", "update-ray": "ray", "lec21": "lec21"}


def load(path):
    return json.loads(path.read_text())


def seconds(stamp):
    result = 0
    for part in stamp.split(":"):
        result = result * 60 + int(part)
    return result


def check_file(record):
    if isinstance(record, str):
        assert (SOURCES / record).is_file(), record
        return
    if record.get("file") and record.get("sha256"):
        path = SOURCES / record["file"]
        assert hashlib.sha256(path.read_bytes()).hexdigest() == record["sha256"], path
    for child in record.get("derived_files", []):
        check_file(child)


course = load(ROOT / "course.json")
state = load(ROOT / "status.json")
mapping = load(SOURCES / "version-map-2021.json")
inventory = load(SOURCES / "schedule-inventory-2021.json")
manifest = load(SOURCES / "manifest-2021.json")
shared = load(SOURCES / "p9-shared/manifest-fragment.json")
lectures = {r["id"]: r for r in course["lectures"]}
labs = {r["id"]: r for r in course["labs"]}
originals = {r["id"]: r for r in load(SOURCES / "manifest.json")["sources"]}
originals.update({r["id"]: r for r in manifest["sources"]})
records = list(manifest["sources"])
for fragment in manifest["source_fragments"]:
    data = load(SOURCES / fragment)
    entries = data["sources"] + data.get("derived_files", []) if "sources" in data else [data]
    records.extend(entries)
    if fragment.startswith("p9-"):
        for record in entries:
            check_file(record)
            if (isinstance(record, dict) and record.get("original_source_id") in originals
                    and originals[record["original_source_id"]].get("file")):
                original = originals[record["original_source_id"]]
                for field in ["sha256", "retrieved_at", "last_modified"]:
                    assert record.get(field) == original.get(field), (record.get("id"), field)
ids = [r["id"] for r in records if isinstance(r, dict) and "id" in r]
assert len(ids) == len(set(ids)), "duplicate source IDs"

for entry in shared["scheduled_topics"]:
    ident = entry["id"]
    fragment = f"p9-{TOPICS[ident]}/manifest-fragment.json"
    assert fragment in manifest["source_fragments"], fragment
    sources = load(SOURCES / fragment)["sources"]
    schedule = (SOURCES / f"schedule-{entry['year']}.html").read_text()
    for link in entry["links"]:
        assert f'href="{link}"' in schedule, link
        url = urljoin(entry["base"], link)
        equivalent = {url}
        if "youtu.be/" in url:
            equivalent.add("https://www.youtube.com/watch?v=" + url.rsplit("/", 1)[-1])
        assert any(r.get("url") in equivalent and r["status"] in {"reviewed", "partial", "blocked"}
                   for r in sources), url
    for kind in ["notes", "materials"]:
        assert state["content"]["lectures"][ident][kind].startswith("complete"), (ident, kind)
    if ident.startswith("update-"):
        assert not (ROOT / "lectures" / ident / "draft.zh.md").exists()
        assert "video" not in lectures[ident]
        assert state["content"]["lectures"][ident]["draft"] == "no_video_listed"
        mapped = next(r for r in mapping["updates"] if r["id"] == ident)
        assert mapped["source_fragment"] == fragment
        assert mapped["official_2026_lecture"] == entry["lecture"]

documents = list(ROOT.glob("lectures/*/*.zh.md"))
complete = partial = 0
for path in documents:
    value = state["content"]["lectures"][path.parent.name][path.name.split(".")[0]]
    complete += value.startswith("complete")
    partial += value.startswith("partial")
assert complete + partial == len(documents)
assert state["artifacts"]["lectureDocumentsPublished"] == len(documents)
assert state["artifacts"]["lectureDocumentsCompleted"] == complete
assert state["artifacts"]["lectureDocumentsPartial"] == partial == 0

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
        assert target.is_file(), (path, target)
for path in ROOT.glob("lectures/*/assets/*.svg"):
    ET.parse(path)

draft = ROOT / "lectures/lec21/draft.zh.md"
if draft.is_file():
    video = state["p9Captions"]["lec21"]["videos"][0]
    metadata = load(ROOT / video["metadata"])
    cues = load(ROOT / video["normalizedCaptions"])
    segments = [(seconds(a), seconds(b)) for a, b in re.findall(
        r"^#{2,3}\s+(\d+(?::\d{2}){1,2})[–—-](\d+(?::\d{2}){1,2})", draft.read_text(), re.M)]
    duration = video["durationSeconds"]
    assert metadata["id"] == video["videoId"] == "bu41Qt9G5Qo"
    assert metadata["duration"] == duration == seconds(lectures["lec21"]["video"]["duration"])
    assert all(metadata.get(k) for k in ["title", "channel", "upload_date", "license"])
    assert set(metadata) <= {"id", "title", "duration", "channel", "channel_id", "uploader", "upload_date", "license", "webpage_url"}
    assert segments[0][0] == 0 and segments[-1][1] == duration
    assert len(cues) == video["cues"] and len(segments) == video["draftSections"]
    assert all(a < b for a, b in segments)
    assert all(segments[i - 1][1] == segments[i][0] for i in range(1, len(segments)))
    assert all(c["end_ms"] >= c["start_ms"] >= 0 for c in cues)
    assert all(cues[i - 1]["start_ms"] <= cues[i]["start_ms"] for i in range(1, len(cues)))
    assert all(sum(a * 1000 <= c["start_ms"] < b * 1000 for a, b in segments) == 1 for c in cues)
    assert cues[0]["start_ms"] == video["firstStartMs"]
    assert max(c["end_ms"] for c in cues) == video["lastEndMs"]
    assert state["content"]["lectures"]["lec21"]["draft"].startswith("complete_caption")
    print("L21:", len(cues), "cues,", len(segments), "sections; raw overrun(ms)", max(0, video["lastEndMs"] - duration * 1000))

assert len(lectures) == 29 and len(labs) == 5
assert state["versions"]["labCodeCommit"] == mapping["lab_commit"] == "513cac0aef010750fc74688da8a395974a83cf7a"
assert state["labTests"] == "not_run" and state["learnerLabCompletion"] == "not_tracked"
assert state["artifacts"]["labDocumentsCompleted"] == len(list(ROOT.glob("labs/*/*.zh.md"))) == 10
assert state["artifacts"]["lectureIllustrationsCompleted"] == len(list(ROOT.glob("lectures/*/assets/*.svg")))
assert len(state["p6Captions"]["lec15"]["videos"]) == 2
for ident in ["lec06", "lec08"]:
    assert state["content"]["lectures"][ident]["notes"] == "not_planned_lab_QA_user_scope"
    assert state["content"]["lectures"][ident]["draft"] == "not_required_lab_QA_user_scope"
assert state["content"]["lectures"]["update-go-patterns"]["materials"] == "complete_FAQ_optional_blog_introductions_CACM_link_only_user_scope"
assert any(r["id"] == "p8-go-cacm-article" and r["status"] == "closed_link_only_user_scope" for r in state["knownIssues"])
assert inventory["lectures"][17]["reading_scope"] == "until Section 3.4"
assert state["phase"].startswith("P9_")
assert (SOURCES / "NEXT-MAINTENANCE-PROMPT.txt").is_file()
print(f"PASS: P9 hashes/provenance, unique source IDs, 8 schedule links, routes/images/SVG, states and counts: {len(documents)} lecture documents ({complete} complete, {partial} partial),10 lab documents. Historical boundaries retained; no experiments.")
