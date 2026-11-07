#!/usr/bin/env python3
"""Fetch the 2020 official inventory and Lecture 1 evidence; no media download."""
import hashlib
import json
import subprocess
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urljoin
from urllib.request import urlopen

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "content/mit-6.s081-2020"
BASE = "https://pdos.csail.mit.edu/6.S081/2020/"


class Schedule(HTMLParser):
    def __init__(self):
        super().__init__()
        self.cells = []
        self.cell = None
        self.link = None

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag == "td":
            self.cell = {"text": "", "links": []}
        if tag == "a" and self.cell is not None:
            self.link = {"label": "", "url": urljoin(BASE + "schedule.html", attrs.get("href", ""))}

    def handle_data(self, data):
        if self.cell is not None:
            self.cell["text"] += data + " "
        if self.link is not None:
            self.link["label"] += data

    def handle_endtag(self, tag):
        if tag == "a" and self.link is not None:
            self.cell["links"].append(self.link)
            self.link = None
        if tag == "td" and self.cell is not None:
            self.cells.append(self.cell)
            self.cell = None


def save_json(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n")


def fetch(item):
    source_id, relative, target = item
    url = urljoin(BASE, relative)
    path = OUT / "sources" / target
    try:
        with urlopen(url, timeout=40) as response:
            data = response.read()
            record = {"id": source_id, "url": url, "resolved_url": response.url,
                      "retrieved_at": datetime.now(timezone.utc).isoformat(),
                      "http_status": response.status, "content_type": response.headers.get("Content-Type"),
                      "last_modified": response.headers.get("Last-Modified"),
                      "file": str(path.relative_to(OUT)), "sha256": hashlib.sha256(data).hexdigest(),
                      "status": "fetched"}
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)
        return record
    except Exception as error:
        return {"id": source_id, "url": url, "status": "blocked", "error": str(error)}


def main():
    items = [("schedule", "schedule.html", "schedule.html"),
             ("lecture1-notes", "lec/l-overview.txt", "l-overview.txt"),
             ("lecture1-examples", "lec/l-overview/", "examples-index.html"),
             ("lab-util", "labs/util.html", "lab-util.html"),
             ("tools", "tools.html", "tools.html"),
             ("xv6-book", "xv6/book-riscv-rev1.pdf", "book-riscv-rev1.pdf")]
    for name in ["copy", "echo", "exec", "fork", "forkexec", "list", "open", "pipe1", "pipe2", "redirect"]:
        items.append((f"example-{name}", f"lec/l-overview/{name}.c", f"examples/{name}.c"))
    with ThreadPoolExecutor(max_workers=4) as pool:
        records = list(pool.map(fetch, items))
    save_json(OUT / "sources/manifest.json", records)
    if next(r for r in records if r["id"] == "schedule")["status"] == "fetched":
        import re
        parser = Schedule()
        parser.feed((OUT / "sources/schedule.html").read_text())
        lectures = []
        for cell in parser.cells:
            match = re.search(r"LEC\s+(\d+)", cell["text"])
            if match:
                number = int(match[1])
                lectures.append({"id": f"lec{number:02}", "number": number,
                                 "schedule_text": " ".join(cell["text"].split()),
                                 "links": cell["links"], "status": "discovered"})
        save_json(OUT / "lecture-index.json", lectures)
        print(f"Official schedule: {len(lectures)} lectures")
    video_url = "https://www.youtube.com/watch?v=L6YqHxYHa7A"
    video = {"url": video_url, "retrieved_at": datetime.now(timezone.utc).isoformat()}
    common = ["yt-dlp", "--skip-download", "--no-playlist", "--socket-timeout", "20", "--retries", "1"]
    try:
        result = subprocess.run(common + ["--dump-json", video_url], capture_output=True, text=True, timeout=90)
        if result.returncode:
            raise RuntimeError(result.stderr[-2000:])
        data = json.loads(result.stdout)
        video.update({k: data.get(k) for k in ["id", "title", "duration", "channel", "upload_date", "license"]})
        video["status"] = "metadata-fetched"
        video["manual_languages"] = list(data.get("subtitles", {}))
        video["english_automatic_languages"] = [k for k in data.get("automatic_captions", {}) if k.startswith("en")]
        result = subprocess.run(common + ["--write-auto-subs", "--sub-langs", "en-orig", "--sub-format", "json3",
                                "-o", str(OUT / "sources/video/lecture1.%(ext)s"), video_url],
                                capture_output=True, text=True, timeout=90)
        caption = OUT / "sources/video/lecture1.en-orig.json3"
        video["captions_status"] = "fetched" if result.returncode == 0 and caption.exists() else "blocked"
        if video["captions_status"] == "blocked":
            video["captions_error"] = result.stderr[-2000:]
        else:
            video["captions_file"] = str(caption.relative_to(OUT))
            video["captions_sha256"] = hashlib.sha256(caption.read_bytes()).hexdigest()
    except (OSError, ValueError, RuntimeError, subprocess.TimeoutExpired) as error:
        video["error"] = str(error)
        video.setdefault("status", "blocked")
        video.setdefault("captions_status", "blocked")
    save_json(OUT / "sources/video-metadata.json", video)
    print(f"Official sources: {sum(r['status'] == 'fetched' for r in records)}/{len(records)}")
    print(f"YouTube: {video['status']}; captions: {video['captions_status']}")


if __name__ == "__main__":
    main()
