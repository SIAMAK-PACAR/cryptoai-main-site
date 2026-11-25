"""
forecast_post.py — the 24h AI forecast as a picture post for the paid Pro Telegram channel.

Called when a new forecast arrives (hourly). Posts at most every FC_POST_HOURS (default 4) so the
channel is not flooded. Direction and likely range only: no entry points, no buy/sell.
Any failure is recorded and never affects the site.
"""
from __future__ import annotations

import io
import os
import threading
import time

from PIL import Image, ImageDraw

import post_card as pc

EVERY_S = float(os.environ.get("FC_POST_HOURS", "4")) * 3600
NAMES = {"BTC": "بیت‌کوین", "ETH": "اتریوم", "SOL": "سولانا", "XRP": "ریپل"}
BIAS_FA = {"up": "تمایل صعودی", "down": "تمایل نزولی", "flat": "خنثی / رنج"}
BIAS_EN = {"up": "Leaning up", "down": "Leaning down", "flat": "Sideways"}
COL = {"up": pc.UP, "down": pc.DOWN, "flat": pc.FLAT}
_lock = threading.Lock()


def usd(v: float) -> str:
    d = 0 if v >= 1000 else 2 if v >= 1 else 4
    return "$" + f"{v:,.{d}f}"


def pct(v: float) -> str:
    return f"{v * 100:+.2f}%"


def render(fc: dict) -> bytes:
    W, H = 1080, 1350
    im = Image.new("RGB", (W, H), pc.BG)
    d = ImageDraw.Draw(im)
    R = W - 60
    d.text((60, 56), "CryptoAI Pro", font=pc._fn(46), fill=(34, 211, 238))
    pc._rtl(d, (R, 50), "پیش‌بینی ۲۴ ساعت آینده", pc._f(52), pc.FG)
    pc._rtl(d, (R, 122), "هوش مصنوعی · ده‌ها مسیر احتمالی قیمت روی کندل‌های ساعتی", pc._f(28, False), pc.MUTED)

    coins = [s for s in ("BTC", "ETH", "SOL", "XRP") if s in fc["coins"]]
    y = 200
    for s in coins:
        c = fc["coins"][s]
        col = COL.get(c["bias"], pc.FLAT)
        d.rounded_rectangle((60, y, R, y + 118), radius=22, fill=pc.PANEL, outline=pc.LINE, width=2)
        d.rounded_rectangle((R - 14, y + 18, R - 6, y + 100), radius=4, fill=col)
        pc._rtl(d, (R - 36, y + 16), f"{NAMES[s]}  ·  {s}", pc._f(36), pc.FG)
        pc._rtl(d, (R - 36, y + 66), BIAS_FA.get(c["bias"], ""), pc._f(30), col)
        d.text((90, y + 18), pct(c["chg_24h"]), font=pc._fn(40), fill=col)
        lo, hi = (c.get("range_24h") or [0, 0])[:2]
        d.text((90, y + 70), f"{usd(lo)} – {usd(hi)}", font=pc._fn(26), fill=pc.MUTED)
        d.text((480, y + 24), f"{round(c['up_share'] * 100)}%", font=pc._fn(36), fill=pc.FG)
        pc._rtl(d, (640, y + 72), "مسیرهای صعودی", pc._f(22, False), pc.MUTED)
        y += 136

    # BTC chart: last 48h + middle path + 80% band
    c = fc["coins"].get("BTC") or fc["coins"][coins[0]]
    top, bot, L, Rr = y + 40, H - 150, 80, R - 20
    d.rounded_rectangle((60, top - 20, R, bot + 20), radius=22, fill=pc.PANEL)
    h, med, p10, p90 = c["history"], c["median"], c["p10"], c["p90"]
    allv = h + p10 + p90
    lo, hi = min(allv), max(allv)
    pad = (hi - lo) * 0.08 or 1
    lo, hi = lo - pad, hi + pad
    n, m = len(h), len(med)
    X = lambda i: L + (Rr - L) * i / (n + m - 1)  # noqa: E731
    Y = lambda v: top + (bot - top) * (1 - (v - lo) / (hi - lo))  # noqa: E731
    last = h[-1]
    band = [(X(n - 1), Y(last))] + [(X(n + i), Y(v)) for i, v in enumerate(p90)] + \
           [(X(n + i), Y(v)) for i, v in reversed(list(enumerate(p10)))]
    over = Image.new("RGBA", im.size, (0, 0, 0, 0))
    ImageDraw.Draw(over).polygon(band, fill=(255, 201, 77, 60))
    im.paste(over, (0, 0), over)
    d = ImageDraw.Draw(im)
    d.line([(X(i), Y(v)) for i, v in enumerate(h)], fill=pc.FG, width=4)
    pts = [(X(n - 1), Y(last))] + [(X(n + i), Y(v)) for i, v in enumerate(med)]
    col = COL.get(c["bias"], pc.FLAT)
    for i in range(len(pts) - 1):
        if i % 2 == 0:
            d.line([pts[i], pts[i + 1]], fill=col, width=5)
    d.line([(X(n - 1), top), (X(n - 1), bot)], fill=pc.LINE, width=2)
    d.ellipse((X(n - 1) - 8, Y(last) - 8, X(n - 1) + 8, Y(last) + 8), fill=pc.FG)
    d.text((L, top - 6), "BTC", font=pc._fn(26), fill=pc.MUTED)
    pc._rtl(d, (Rr, top - 6), "۴۸ ساعت گذشته · مسیر میانی · محدودهٔ ۸۰٪", pc._f(22, False), pc.MUTED)

    pc._rtl(d, (R, H - 100), "تحلیل آموزشی است؛ سیگنال خرید یا فروش نیست.", pc._f(26, False), pc.MUTED)
    d.text((60, H - 96), "Not a buy/sell signal", font=pc._fn(24), fill=pc.MUTED)
    out = io.BytesIO()
    im.save(out, "PNG", optimize=True)
    return out.getvalue()


def caption(fc: dict) -> str:
    lines = ["🔮 <b>پیش‌بینی ۲۴ ساعت آینده · CryptoAI Pro</b>", ""]
    for s in ("BTC", "ETH", "SOL", "XRP"):
        c = fc["coins"].get(s)
        if not c:
            continue
        lo, hi = (c.get("range_24h") or [0, 0])[:2]
        e = "🟢" if c["bias"] == "up" else "🔴" if c["bias"] == "down" else "⚪️"
        lines.append(f"{e} {NAMES[s]} ({s}): {BIAS_FA[c['bias']]} · مسیر میانی {pct(c['chg_24h'])} · "
                     f"محدودهٔ محتمل {usd(lo)}–{usd(hi)}")
    lines += ["", "🇬🇧 " + " · ".join(f"{s} {BIAS_EN[fc['coins'][s]['bias']]} {pct(fc['coins'][s]['chg_24h'])}"
                                    for s in ("BTC", "ETH", "SOL", "XRP") if s in fc["coins"]),
              "", pc.DISCLAIMER]
    return "\n".join(lines)


def maybe_post(fc: dict) -> None:
    """Post to the Pro channel if it is set up and the last post is old enough. Runs in a thread."""
    def run():
        try:
            import pro
            import telegram_bot as tb
            if not pro.ready():
                return
            with _lock:
                if time.time() - float(pro.S.get("fc_posted") or 0) < EVERY_S - 300:
                    return
                pro.S["fc_posted"] = time.time()
            tb.send_photo(pro.cfg()["pro"], render(fc), caption(fc))
            pro.backup()
        except Exception as e:
            try:
                import pro
                pro.S["last_error"] = f"forecast post: {str(e)[:150]}"
            except Exception:
                pass
    threading.Thread(target=run, daemon=True).start()
