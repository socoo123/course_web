"""Acquire only files listed by the fixed official repository tree; never execute them."""
import concurrent.futures
import hashlib
import json
import pathlib
import subprocess
import urllib.request
from datetime import datetime, timezone

ROOT = pathlib.Path(__file__).parent
SHA = "de53a9f979a6ee35f7d13a5e1aadee5ea1afc58e"
tree = json.loads((ROOT / "tree.json").read_text())["tree"]
paths = [x["path"] for x in tree if x["type"] == "blob" and (
    (x["path"].startswith("lecture_") and x["path"].endswith((".py", ".pdf")))
    or x["path"].startswith("var/traces/lecture_")
    or x["path"] in {"README.md", "references.py", "pyproject.toml", "uv.lock", "index.html", "modal_execute.py"}
)]

def acquire(path):
    url = f"https://raw.githubusercontent.com/stanford-cs336/lectures/{SHA}/{path}"
    dest = ROOT / "raw" / path.replace("README.md", "README.txt")
    dest.parent.mkdir(parents=True, exist_ok=True)
    result = {"repository_path": path, "url": url, "commit": SHA, "retrieved_at": datetime.now(timezone.utc).isoformat()}
    try:
        data = urllib.request.urlopen(url, timeout=90).read()
        dest.write_bytes(data)
        result.update(file=str(dest.relative_to(ROOT.parent)), sha256=hashlib.sha256(data).hexdigest(), bytes=len(data), status="acquired_not_read")
        if dest.suffix == ".pdf":
            text = ROOT / (dest.stem + ".txt")
            subprocess.run(["pdftotext", "-layout", str(dest), str(text)], check=True)
            result["text_file"] = str(text.relative_to(ROOT.parent))
    except Exception as exc:
        result.update(status="acquisition_failed", error=str(exc))
    return result

with concurrent.futures.ThreadPoolExecutor(max_workers=4) as pool:
    records = list(pool.map(acquire, paths))
(ROOT / "acquisition.json").write_text(json.dumps({"commit": SHA, "files": records}, indent=2) + "\n")
print(json.dumps({"files": len(records), "bytes": sum(r.get("bytes", 0) for r in records), "failures": [r for r in records if r["status"] != "acquired_not_read"]}, indent=2))
