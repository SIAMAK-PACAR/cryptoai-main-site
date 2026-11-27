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


def _verify(url: str, size: int) -> bool:
    """The host must serve the exact file bytes (not an HTML download page)."""
    r = subprocess.run(["curl", "-sSL", "-A", "Mozilla/5.0", "-o", "/tmp/_dl_check", "-w", "%{http_code} %{content_type}", url],
                       capture_output=True, text=True)
    ok = r.returncode == 0 and r.stdout.startswith("200") and Path("/tmp/_dl_check").exists() \
        and Path("/tmp/_dl_check").stat().st_size == size
    print(f"  verify {url}: {r.stdout.strip()} ok={ok}", flush=True)
    return ok


def upload(path: Path) -> str:
    """Public hosting so the YouTube uploader can download the file. Several hosts, each verified."""
    size = path.stat().st_size
    hosts = [
        ("catbox", ["curl", "-sS", "-F", "reqtype=fileupload", "-F", f"fileToUpload=@{path}", "https://catbox.moe/user/api.php"]),
        ("litterbox", ["curl", "-sS", "-F", "reqtype=fileupload", "-F", "time=72h", "-F", f"fileToUpload=@{path}",
                       "https://litterbox.catbox.moe/resources/internals/api.php"]),
        ("0x0", ["curl", "-sS", "-A", "cryptoai-academy/1.0", "-F", f"file=@{path}", "-F", "expires=72", "https://0x0.st"]),
        ("uguu", ["curl", "-sS", "-F", f"files[]=@{path}", "https://uguu.se/upload?output=text"]),
    ]
    for name, cmd in hosts:
        for attempt in range(2):
            r = subprocess.run(cmd, capture_output=True, text=True)
            out = r.stdout.strip().splitlines()[0] if r.stdout.strip() else ""
            print(f"  {name}: rc={r.returncode} out={out[:120]!r} err={r.stderr.strip()[:200]!r}", flush=True)
            if out.startswith("https://") and _verify(out, size):
                return out
            time.sleep(4)
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
