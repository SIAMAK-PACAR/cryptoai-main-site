"""CI helper: render the next unbuilt lesson, host the two MP4s temporarily, write academy/status/<id>.json.

The YouTube upload itself is triggered separately (Make scenario), so no webhook or key lives in this repo.
"""
from __future__ import annotations

import json
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent


def upload(path: Path) -> str:
    """Temporary public hosting (72h) so the uploader can download the file. Two hosts for safety."""
    tries = [
        ["curl", "-sS", "--fail", "-F", "reqtype=fileupload", "-F", "time=72h", "-F", f"fileToUpload=@{path}",
         "https://litterbox.catbox.moe/resources/internals/api.php"],
        ["curl", "-sS", "--fail", "-F", f"file=@{path}", "https://tmpfiles.org/api/v1/upload"],
    ]
    for cmd in tries:
        for attempt in range(3):
            r = subprocess.run(cmd, capture_output=True, text=True)
            out = r.stdout.strip()
            if r.returncode == 0 and out:
                if out.startswith("https://"):
                    return out
                try:
                    u = json.loads(out)["data"]["url"]
                    return u.replace("tmpfiles.org/", "tmpfiles.org/dl/").replace("http://", "https://")
                except Exception:
                    pass
            time.sleep(5)
    raise RuntimeError(f"upload failed for {path.name}")


def main():
    want = sys.argv[1] if len(sys.argv) > 1 else ""
    eps = sorted(p.stem for p in (ROOT / "episodes").glob("ep*.json"))
    todo = [e for e in eps if not (ROOT / "status" / f"{e}.json").exists()]
    if want:
        todo = [want] if want in eps else []
    if not todo:
        print("nothing to build"); return
    ep = todo[0]
    subprocess.run([sys.executable, str(ROOT / "render.py"), ep], check=True)
    meta = json.loads((ROOT / "out" / f"{ep}-meta.json").read_text())
    meta["long_url"] = upload(ROOT / "out" / f"{ep}-long.mp4")
    meta["short_url"] = upload(ROOT / "out" / f"{ep}-short.mp4")
    meta["built_at"] = datetime.now(timezone.utc).isoformat(timespec="seconds")
    meta["published"] = False
    (ROOT / "status").mkdir(exist_ok=True)
    (ROOT / "status" / f"{ep}.json").write_text(json.dumps(meta, ensure_ascii=False, indent=1))
    print(json.dumps(meta, ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main()
