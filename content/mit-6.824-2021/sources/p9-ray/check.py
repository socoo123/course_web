"""Minimal local checks; no network, build, git operations or shared writes."""
import hashlib
import json
import re
from pathlib import Path

HERE = Path(__file__).resolve().parent
SOURCES = HERE.parent
COURSE = SOURCES.parent
fragment = json.loads((HERE / "manifest-fragment.json").read_text())
old = {s["id"]: s for s in json.loads((SOURCES / "manifest.json").read_text())["sources"]}
ids = [s["id"] for s in fragment["sources"]]
assert len(ids) == len(set(ids)) and all(i.startswith("p9-ray-") for i in ids)
messages = []
for source in fragment["sources"]:
    path = SOURCES / source["file"]
    assert path.is_file(), path
    assert hashlib.sha256(path.read_bytes()).hexdigest() == source["sha256"], path
    original = old[source["original_source_id"]]
    assert source["url"] == original["url"]
    if source["id"] != "p9-ray-faq":
        for field in ("retrieved_at", "last_modified", "file", "sha256"):
            assert source[field] == original[field], (source["id"], field)
    messages.append(f"PASS source/hash/provenance: {source['id']}")

faq = next(s for s in fragment["sources"] if s["id"] == "p9-ray-faq")
acquired = json.loads((HERE / "acquisition.json").read_text())
for field in ("retrieved_at", "last_modified", "sha256", "file", "final_url", "http_status", "etag", "bytes"):
    assert acquired[field] == faq[field], field
assert len((SOURCES / faq["file"]).read_text().splitlines()) == 105
assert len(re.findall(r"^Q:", (SOURCES / faq["file"]).read_text(), re.M)) == 14
schedule = (SOURCES / "schedule-2026.html").read_text().splitlines()
entry = "\n".join(schedule[240:243])
for link in ("notes/l-ray.txt", "papers/ray.pdf", "papers/ray-faq.txt"):
    assert f'href="{link}"' in entry
assert "LEC 18 (fk)" in entry and "2026-4-23" in entry and "Ray (2021)" in entry
messages.append("PASS FAQ GET metadata/105 lines/14 questions; exact L18 links/date")

lecture_ids = {lec["id"] for lec in json.loads((COURSE / "course.json").read_text())["lectures"]}
for doc in fragment["documents"]:
    path = COURSE / doc["file_relative_to_course"]
    text = path.read_text()
    assert text.startswith("---\n") and text.count("\n---\n") >= 1
    assert text.count("```") % 2 == 0
    assert text.count("<details>") == text.count("</details>")
    assert not any(line.rstrip() != line for line in text.splitlines())
    for heading in re.findall(r"^## (.+)$", text, re.M):
        if re.search(r"引用|参考|来源|出处|许可|版权|致谢|References|Sources", heading):
            assert heading == "引用与来源", heading
    for target in re.findall(r"#/c/mit-6\.824-2021/lec/([^?)\s]+)", text):
        assert target in lecture_ids, target
    for image in re.findall(r"!\[[^]]*\]\(([^)]+)\)", text):
        assert (path.parent / image).exists(), image
    digest = hashlib.sha256(path.read_bytes()).hexdigest()
    messages.append(f"PASS document/frontmatter/fences/routes/whitespace: {doc['file_relative_to_course']} ({len(text.splitlines())} lines; sha256 {digest})")
assert not (COURSE / "lectures/update-ray/draft.zh.md").exists()
messages.append("PASS no draft; no figures/assets require publication")
messages.append("Scope: static source/content checks only; no Ray, TLA+, experiments, git or build executed.")
report = "\n".join(messages) + "\n"
(HERE / "validation.txt").write_text(report)
print(report)
