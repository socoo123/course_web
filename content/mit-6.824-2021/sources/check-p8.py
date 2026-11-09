"""P8 written-source provenance and content integration checks; no lab execution."""
import hashlib
import json
import re
import xml.etree.ElementTree as ET
from pathlib import Path
from urllib.parse import urljoin

ROOT = Path(__file__).resolve().parent.parent
SOURCES = ROOT / "sources"
TOPICS = ["paxos", "go-patterns", "verification", "bft"]


def load(path):
    return json.loads(path.read_text())


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
shared = load(SOURCES / "p8-shared/manifest-fragment.json")
lectures = {x["id"]: x for x in course["lectures"]}
labs = {x["id"]: x for x in course["labs"]}
records = list(manifest["sources"])
originals = {r["id"]: r for r in load(SOURCES / "manifest.json")["sources"]}
originals.update({r["id"]: r for r in manifest["sources"]})
for fragment in manifest["source_fragments"]:
    data = load(SOURCES / fragment)
    entries = data["sources"] + data.get("derived_files", []) if "sources" in data else [data]
    records.extend(entries)
    if fragment.startswith("p8-"):
        for record in entries:
            check_file(record)
            if isinstance(record, dict) and record.get("original_source_id") in originals:
                original = originals[record["original_source_id"]]
                for field in ["sha256", "retrieved_at", "last_modified"]:
                    assert record.get(field) == original.get(field), (record.get("id"), field)
ids = [r["id"] for r in records if isinstance(r, dict) and "id" in r]
assert len(ids) == len(set(ids)), "duplicate source IDs"
assert "p8-shared/manifest-fragment.json" in manifest["source_fragments"]

schedule = (SOURCES / "schedule-2026.html").read_text()
for topic, entry in zip(TOPICS, shared["scheduled_topics"]):
    ident = "update-" + topic
    assert entry["id"] == ident
    fragment = f"p8-{topic}/manifest-fragment.json"
    assert fragment in manifest["source_fragments"], ident
    sources = load(SOURCES / fragment)["sources"]
    for link in entry["links"]:
        assert f'href="{link}"' in schedule, link
        url = urljoin("https://pdos.csail.mit.edu/6.824/", link)
        matches = [r for r in sources if r.get("url") == url]
        assert matches, (ident, url)
        assert any(r["status"] in {"reviewed", "partial", "blocked"} for r in matches), url
    assert not (ROOT / "lectures" / ident / "draft.zh.md").exists(), ident
    assert "video" not in lectures[ident], ident
    assert state["content"]["lectures"][ident]["draft"] == "no_video_listed"
    for kind in ["notes", "materials"]:
        value = state["content"]["lectures"][ident][kind]
        if (ident, kind) == ("update-go-patterns", "materials"):
            assert value == "partial_FAQ_complete_CACM_article_blocked"
            assert any(r.get("id") == "p8-go-cacm-original" and r["status"] == "blocked"
                       and r["http_status"] == 403 for r in sources)
        else:
            assert value.startswith("complete"), (ident, kind)
    mapped = next(x for x in mapping["updates"] if x["id"] == ident)
    assert mapped["official_2026_lecture"] == entry["lecture"]
    assert mapped["source_fragment"] == fragment

documents = [ROOT / "lectures" / ("update-" + topic) / f"{kind}.zh.md"
             for topic in TOPICS for kind in ["notes", "materials"]]
for path in documents + [ROOT / "resources.zh.md", ROOT / "lectures/lec10/notes.zh.md"]:
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
            assert kind == "lec" and state["content"]["lectures"][ident][view] == "not_started", (path, target)
for path in ROOT.glob("lectures/*/assets/*.svg"):
    ET.parse(path)

assert len(lectures) == 29 and len(labs) == 5
assert state["versions"]["labCodeCommit"] == mapping["lab_commit"] == "513cac0aef010750fc74688da8a395974a83cf7a"
assert state["labTests"] == "not_run" and state["learnerLabCompletion"] == "not_tracked"
assert state["artifacts"]["lectureDocumentsPublished"] == len(list(ROOT.glob("lectures/*/*.zh.md"))) == 62
assert state["artifacts"]["lectureDocumentsCompleted"] == 61
assert state["artifacts"]["lectureDocumentsPartial"] == 1
assert state["artifacts"]["labDocumentsCompleted"] == len(list(ROOT.glob("labs/*/*.zh.md"))) == 10
assert state["artifacts"]["lectureIllustrationsCompleted"] == len(list(ROOT.glob("lectures/*/assets/*.svg")))
assert len(state["p6Captions"]["lec15"]["videos"]) == 2
for ident in ["lec06", "lec08"]:
    assert state["content"]["lectures"][ident]["notes"] == "pending_sources"
    assert state["content"]["lectures"][ident]["draft"] == "no_video_listed"
for ident in ["update-lambda", "update-ray", "lec21"]:
    assert state["content"]["lectures"][ident]["notes"] == "not_started"
assert inventory["lectures"][17]["reading_scope"] == "until Section 3.4"
assert state["phase"] == "P8_complete_with_CACM_gap"
assert (SOURCES / "NEXT-P9-PROMPT.txt").is_file()
print("PASS: 8 P8 documents, source hashes/IDs, exact schedule links, routes/images/SVG, metadata/state and totals (62 published lecture documents: 61 complete + 1 partial; 10 lab documents). CACM403 gap retained. No protocol, proof-tool or lab execution claimed.")
