"""
youtube_shorts.py — one bilingual (Persian + English) YouTube Short per day, free.

The daily social kit already renders a Persian and an English 15-second reel. This module
joins them into one 30-second Short, serves it at a temporary public URL, and sends the
URL, title and description to a Make.com webhook (free plan). The Make scenario uploads it
to the CryptoAI YouTube channel with Make's verified YouTube app, so videos are public.

Render env: MAKE_YT_WEBHOOK = the webhook URL from the Make scenario. Without it nothing is
sent. Any failure here is reported to the admin and never affects the site or Telegram.
"""
from __future__ import annotations

import os
import secrets
import subprocess
import tempfile
import threading
import time
from pathlib import Path

_videos: dict = {}            # key -> (mp4 bytes, expires)
_lock = threading.Lock()
_rt = {"last": None, "last_error": None}
KEEP_S = 6 * 3600             # YouTube/Make fetch the file within minutes; keep it a few hours


def webhook() -> str:
    return os.environ.get("MAKE_YT_WEBHOOK", "").strip()


def ready() -> bool:
    return webhook().startswith("https://")


def video_get(key: str):
    item = _videos.get(key)
    if not item or item[1] < time.time():
        return None
    return item[0]


def _host(mp4: bytes) -> str:
    import post_card as pc
    key = secrets.token_urlsafe(16)
    with _lock:
        for k in [k for k, v in _videos.items() if v[1] < time.time()]:
            _videos.pop(k, None)
        _videos[key] = (mp4, time.time() + KEEP_S)
    return f"{pc.site_url()}/social/video/{key}.mp4"


def join(fa_mp4: bytes, en_mp4: bytes) -> bytes:
    """Persian reel, then English reel, as one MP4 (same size/codec, so no re-encode)."""
    import imageio_ffmpeg
    with tempfile.TemporaryDirectory(prefix="cryptoai_short_") as d:
        p = Path(d)
        (p / "a.mp4").write_bytes(fa_mp4)
        (p / "b.mp4").write_bytes(en_mp4)
        (p / "list.txt").write_text("file 'a.mp4'\nfile 'b.mp4'\n")
        out = p / "short.mp4"
        subprocess.run([imageio_ffmpeg.get_ffmpeg_exe(), "-hide_banner", "-loglevel", "error", "-y",
                        "-f", "concat", "-safe", "0", "-i", str(p / "list.txt"), "-c", "copy",
                        "-movflags", "+faststart", str(out)], check=True, capture_output=True, timeout=60)
        data = out.read_bytes()
    if not data:
        raise RuntimeError("empty short")
    return data


def _title(news: dict) -> str:
    fa = (news.get("t") or "").strip()
    en = (news.get("en_t") or "").strip()
    t = f"{fa} | {en}" if fa and en and fa != en else (fa or en)
    t = t.replace("<", "").replace(">", "")       # YouTube rejects angle brackets in titles
    return (t[:92].rstrip() + "…") if len(t) > 93 else t


def _links_block() -> str:
    """Website, both Telegram channels and Pro, first in the description (YouTube shows the top lines)."""
    import social
    site, fa, en = social.promo_links()
    lines = []
    if site:
        lines.append(f"🌐 سایت | Website: {site}")
    if fa:
        lines.append(f"🇮🇷 کانال تلگرام فارسی: {fa}")
    if en:
        lines.append(f"🌍 English Telegram: {en}")
    if site:
        lines.append(f"🔒 پیش‌بینی ۲۴ ساعتهٔ هوش مصنوعی و خبر فوری | 24h AI forecast & instant alerts (Pro): {site}/pro")
    return "\n".join(lines)


def _description(news: dict, assets: list) -> str:
    import social
    fa = social.caption(news, assets, "fa")
    en = social.caption(news, assets, "en")
    links = _links_block()
    d = (f"{links}\n\n" if links else "") + f"{fa}\n\n— — —\n\n{en}\n\n#shorts #crypto #bitcoin #کریپتو #بیت_کوین"
    return d.replace("<", "").replace(">", "")[:4900]


def publish(fa_mp4: bytes, en_mp4: bytes, news: dict, assets: list) -> str:
    """Join, host and hand the Short to the Make webhook. Returns a short status line."""
    if not ready():
        return ""
    import requests
    try:
        url = _host(join(fa_mp4, en_mp4))
        # Right after a deploy the public URL may still reach the *old* instance, which doesn't
        # hold this video in memory. Wait until the URL really serves it before calling Make.
        ok = False
        for _ in range(24):                          # up to ~4 minutes
            try:
                h = requests.head(url, timeout=20, allow_redirects=True)
                if h.status_code == 200:
                    ok = True
                    break
            except Exception:
                pass
            time.sleep(10)
        if not ok:
            raise RuntimeError("video URL not reachable yet (deploy in progress?)")
        payload = {"video_url": url, "title": _title(news), "description": _description(news, assets),
                   "tags": "crypto,bitcoin,ethereum,crypto news,کریپتو,بیت کوین,اخبار ارز دیجیتال,CryptoAI"}
        r = requests.post(webhook(), json=payload, timeout=60)
        r.raise_for_status()
        _rt["last"], _rt["last_error"] = time.strftime("%Y-%m-%d %H:%M"), None
        return "✅ شورت دوزبانهٔ یوتیوب فرستاده شد."
    except Exception as e:
        _rt["last_error"] = f"{type(e).__name__}: {e}"[:200]
        return f"⚠️ شورت یوتیوب فرستاده نشد: {_rt['last_error']}"


def status() -> dict:
    return {"ready": ready(), "last": _rt["last"], "last_error": _rt["last_error"]}
