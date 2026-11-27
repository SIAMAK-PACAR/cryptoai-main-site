"""CryptoAI Academy: render one lesson (long 16:9 video + vertical Short) from episodes/<id>.json.

    python academy/render.py ep01            # neural English voice (edge-tts), needs internet
    python academy/render.py ep01 --silent   # no voice, timing estimated (for local previews)

Output: academy/out/<id>-long.mp4, academy/out/<id>-short.mp4, academy/out/<id>-meta.json
Style: clean dark chart desk; each callout/lens appears only while that point is narrated, then fades.
"""
from __future__ import annotations

import asyncio
import json
import math
import os
import random
import subprocess
import sys
import tempfile
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter, ImageFont, features

ROOT = Path(__file__).resolve().parent
FONTS = ROOT / "fonts"
OUT = ROOT / "out"
FFMPEG = os.environ.get("FFMPEG", "ffmpeg")

W, H, FPS = 1280, 720, 24
K = W / 1920                      # design in 1920x1080 units, render at 1280x720
VOICE = os.environ.get("ACADEMY_VOICE", "en-US-AndrewMultilingualNeural")

BG = (9, 12, 19); PANEL = (15, 19, 29); GRID = (27, 33, 46); TXT = (232, 236, 243); MUTE = (122, 133, 153)
UP = (38, 166, 154); DN = (239, 83, 80); ACC = (242, 183, 5); BLUE = (77, 163, 255); PURP = (176, 128, 255)
COL = {"up": UP, "dn": DN, "acc": ACC, "blue": BLUE, "purp": PURP}

RAQM = features.check("raqm")
FAKW = dict(direction="rtl", language="fa") if RAQM else {}
_fc: dict = {}


def s(v):                      # design units -> pixels
    return int(round(v * K))


def F(name, size):
    key = (name, size)
    if key not in _fc:
        _fc[key] = ImageFont.truetype(str(FONTS / name), max(6, s(size)))
    return _fc[key]


def FA(size, bold=True):
    key = ("fa", size, bold)
    if key not in _fc:
        _fc[key] = ImageFont.truetype(str(FONTS / ("Vazirmatn-Bold.ttf" if bold else "Vazirmatn-Regular.ttf")), s(size),
                                      layout_engine=ImageFont.Layout.RAQM if RAQM else ImageFont.Layout.BASIC)
    return _fc[key]


def ease(a):
    a = max(0.0, min(1.0, a)); return a * a * (3 - 2 * a)


def appear(t, t0, d=0.45):
    return ease((t - t0) / d)


def fade(im, fn, a):
    """Draw fn(layer) on a transparent layer and composite it with opacity a."""
    if a <= 0.01:
        return
    ov = Image.new("RGBA", im.size, (0, 0, 0, 0)); fn(ov)
    if a < 0.99:
        ov.putalpha(ov.getchannel("A").point(lambda v: int(v * a)))
    im.alpha_composite(ov)


def glow(im, cx, cy, r, col, a=1.0, width=3):
    pad = int(r + s(30)); ov = Image.new("RGBA", (2 * pad, 2 * pad), (0, 0, 0, 0)); d = ImageDraw.Draw(ov)
    d.ellipse((pad - r, pad - r, pad + r, pad + r), outline=col + (int(150 * a),), width=s(10))
    ov = ov.filter(ImageFilter.GaussianBlur(s(8))); d = ImageDraw.Draw(ov)
    d.ellipse((pad - r, pad - r, pad + r, pad + r), outline=col + (int(255 * a),), width=max(1, s(width)))
    im.alpha_composite(ov, (int(cx - pad), int(cy - pad)))


def pill(d, xy, text, font, fg, bg, pad=(14, 7)):
    x, y = xy; tw = d.textlength(text, font=font); bb = font.getbbox("Ag")
    h = bb[3] - bb[1] + s(pad[1]) * 2
    d.rounded_rectangle((x, y, x + tw + s(pad[0]) * 2, y + h), radius=h // 2, fill=bg)
    d.text((x + s(pad[0]), y + s(pad[1]) - bb[1]), text, font=font, fill=fg)
    return x + tw + s(pad[0]) * 2


def card(d, box, col=None, fill=PANEL, r=16, width=2):
    d.rounded_rectangle(box, radius=s(r), fill=fill, outline=(col + (255,)) if col else None, width=s(width) if col else 0)


def wrap(d, text, font, maxw):
    out, line = [], ""
    for w_ in text.split():
        t = (line + " " + w_).strip()
        if d.textlength(t, font=font) <= maxw or not line:
            line = t
        else:
            out.append(line); line = w_
    if line:
        out.append(line)
    return out


# ------------------------------------------------------------------ icons
def icon_person(d, cx, cy, r, col):
    d.ellipse((cx - r * 0.38, cy - r * 0.95, cx + r * 0.38, cy - r * 0.2), fill=col)
    d.pieslice((cx - r * 0.75, cy - r * 0.05, cx + r * 0.75, cy + r * 1.35), 180, 360, fill=col)


def icon_bank(d, cx, cy, r, col):
    d.polygon([(cx - r, cy - r * 0.35), (cx, cy - r), (cx + r, cy - r * 0.35)], fill=col)
    for k in range(4):
        x = cx - r * 0.7 + k * r * 0.47
        d.rectangle((x - r * 0.09, cy - r * 0.2, x + r * 0.09, cy + r * 0.6), fill=col)
    d.rectangle((cx - r, cy + r * 0.68, cx + r, cy + r * 0.85), fill=col)


def icon_doc(d, cx, cy, r, col, lines=3):
    d.rounded_rectangle((cx - r * 0.7, cy - r, cx + r * 0.7, cy + r), radius=max(1, int(r * 0.15)), outline=col, width=max(1, s(3)))
    for k in range(lines):
        y = cy - r * 0.45 + k * r * 0.42
        d.line((cx - r * 0.4, y, cx + r * 0.4, y), fill=col, width=max(1, s(3)))


# ------------------------------------------------------------------ candles (synthetic example data)
def make_candles(n, seed=7):
    rnd = random.Random(seed); p = 100.0; out = []
    drift = [0.5] * 10 + [-0.9] * 9 + [0.2] * 6 + [1.2] * 10 + [-1.4] * 6 + [0.9] * 20
    for i in range(n):
        dd = drift[i] if i < len(drift) else 0.4
        o = p; c = o + dd + rnd.uniform(-1.6, 1.6)
        h = max(o, c) + rnd.uniform(0.3, 1.8); l = min(o, c) - rnd.uniform(0.3, 1.8)
        out.append((o, h, l, c)); p = c
    return out


# ------------------------------------------------------------------ scene renderers
class Ctx:
    def __init__(self, ep, scene, idx, starts, ends, t0, t1):
        self.ep, self.sc, self.idx, self.starts, self.ends, self.t0, self.t1 = ep, scene, idx, starts, ends, t0, t1

    def L(self, i):                    # start time of line i (scene-relative)
        i = max(0, min(i, len(self.starts) - 1)); return self.starts[i]

    def active(self, t):
        k = 0
        for i, st in enumerate(self.starts):
            if t >= st - 0.05:
                k = i
        return k


def heading(im, c, t):
    a = appear(t, 0)
    def fn(ov):
        d = ImageDraw.Draw(ov)
        pill(d, (s(64), s(46)), f"LESSON {c.ep['number']:02d}  ·  {c.ep['level']}", F("Inter-SemiBold.otf", 19), ACC, (40, 33, 10))
        d.text((s(64), s(92)), c.sc.get("heading", ""), font=F("InterDisplay-Bold.otf", 50), fill=TXT)
    fade(im, fn, a)


def sc_title(im, c, t):
    d = ImageDraw.Draw(im)
    a1, a2, a3 = appear(t, 0.1), appear(t, 0.5), appear(c.L(1), 0) * appear(t, c.L(1))
    def p1(ov):
        dd = ImageDraw.Draw(ov); pill(dd, (s(160), s(330)), f"LESSON {c.ep['number']:02d}  ·  {c.ep['level']}",
                                       F("Inter-SemiBold.otf", 24), ACC, (40, 33, 10), (18, 9))
    def p2(ov):
        dd = ImageDraw.Draw(ov); y = s(400) + int((1 - a2) * s(20))
        dd.text((s(156), y), c.ep["title"], font=F("InterDisplay-Black.otf", 120), fill=TXT)
    def p3(ov):
        dd = ImageDraw.Draw(ov)
        dd.text((s(160), s(560)), c.ep.get("subtitle", ""), font=F("Inter-Regular.otf", 34), fill=MUTE)
        dd.rounded_rectangle((s(160), s(630), s(160) + int(s(520) * a3), s(636)), radius=s(3), fill=BLUE)
    fade(im, p1, a1); fade(im, p2, a2); fade(im, p3, appear(t, 1.0))


def sc_flow(im, c, t):
    heading(im, c, t)
    nodes = c.sc["nodes"]; n = len(nodes); cy = s(470); xs = [s(330 + i * (1260 / max(1, n - 1))) for i in range(n)]
    span = max(0.6, c.L(1) - 0.2) if len(c.starts) > 1 else 2.0
    red = t >= c.L(2) if len(c.starts) > 2 else False
    for i, (label, *_r) in enumerate(nodes):
        a = appear(t, i * span / n)
        if i > 0:
            def ar(ov, i=i):
                dd = ImageDraw.Draw(ov); x0, x1 = xs[i - 1] + s(130), xs[i] - s(130)
                dd.line((x0, cy, x1 - s(16), cy), fill=MUTE, width=s(4))
                dd.polygon([(x1, cy), (x1 - s(22), cy - s(13)), (x1 - s(22), cy + s(13))], fill=MUTE)
            fade(im, ar, a)
        bank = i == n // 2
        col = (DN if red else ACC) if bank else BLUE
        def nd(ov, i=i, label=label, bank=bank, col=col):
            dd = ImageDraw.Draw(ov); x = xs[i]
            card(dd, (x - s(120), cy - s(120), x + s(120), cy + s(120)), col if bank else None)
            (icon_bank if bank else icon_person)(dd, x, cy - s(20), s(52), col)
            f = F("Inter-SemiBold.otf", 28); dd.text((x - dd.textlength(label, font=f) / 2, cy + s(60)), label, font=f, fill=TXT)
        fade(im, nd, a)
    bx = xs[n // 2]
    if len(c.starts) > 1:
        a = appear(t, c.L(1))
        def led(ov):
            dd = ImageDraw.Draw(ov); y = cy + s(170)
            card(dd, (bx - s(210), y, bx + s(210), y + s(150)), ACC)
            icon_doc(dd, bx - s(150), y + s(75), s(42), ACC)
            dd.text((bx - s(90), y + s(30)), "LEDGER", font=F("Inter-Bold.otf", 26), fill=ACC)
            dd.text((bx - s(90), y + s(72)), c.sc.get("note", ""), font=F("Inter-Regular.otf", 20), fill=TXT)
        fade(im, led, a)
        if c.L(1) <= t < (c.L(2) if len(c.starts) > 2 else 1e9):
            glow(im, bx, cy, s(150), ACC, a)
    if red:
        a = appear(t, c.L(2))
        glow(im, bx, cy, s(150), DN, a)
        for k, w_ in enumerate(("FREEZE", "DELAY", "BLOCK")):
            ak = appear(t, c.L(2) + 0.35 * k)
            def bd(ov, k=k, w_=w_):
                dd = ImageDraw.Draw(ov); pill(dd, (bx + s(150), cy - s(150) + k * s(58)), "✕ " + w_ if False else w_,
                                              F("Inter-Bold.otf", 20), (255, 255, 255), DN)
            fade(im, bd, ak)


def _net_pts(n=14):
    rnd = random.Random(3); pts = []
    for i in range(n):
        ang = 2 * math.pi * i / n + rnd.uniform(-0.12, 0.12)
        rr = rnd.uniform(0.82, 1.0)
        pts.append((960 + math.cos(ang) * 560 * rr, 560 + math.sin(ang) * 300 * rr))
    return pts


NET = _net_pts()


def sc_network(im, c, t):
    heading(im, c, t)
    # line 0: the bank in the middle, crossed out
    a0 = appear(t, 0.1); x0 = out_t = None
    fade_bank = 1 - appear(t, c.L(1) + 0.3) * 0.75
    def bk(ov):
        dd = ImageDraw.Draw(ov); icon_bank(dd, s(960), s(560), s(70), MUTE)
        k = appear(t, 0.6)
        if k > 0:
            dd.line((s(880), s(480), s(880) + s(160) * k, s(480) + s(160) * k), fill=DN, width=s(10))
            dd.line((s(1040), s(480), s(1040) - s(160) * k, s(480) + s(160) * k), fill=DN, width=s(10))
    fade(im, bk, a0 * fade_bank)
    if len(c.starts) < 2:
        return
    span = max(1.0, (c.starts[2] if len(c.starts) > 2 else c.L(1) + 3) - c.L(1) - 0.4)
    n = len(NET)
    for i in range(n):
        ai = appear(t, c.L(1) + span * i / n, 0.35)
        if ai <= 0:
            continue
        j = (i + 1) % n; k2 = (i + 4) % n
        def ln(ov, i=i, j=j, k2=k2):
            dd = ImageDraw.Draw(ov)
            for q in (j, k2):
                dd.line((s(NET[i][0]), s(NET[i][1]), s(NET[q][0]), s(NET[q][1])), fill=GRID + (255,), width=s(3))
        fade(im, ln, ai)
    for i in range(n):
        ai = appear(t, c.L(1) + span * i / n, 0.35)
        if ai <= 0:
            continue
        def nd(ov, i=i):
            dd = ImageDraw.Draw(ov); x, y = s(NET[i][0]), s(NET[i][1])
            dd.ellipse((x - s(34), y - s(34), x + s(34), y + s(34)), fill=PANEL, outline=BLUE, width=s(3))
            icon_doc(dd, x, y, s(17), BLUE, 2)
        fade(im, nd, ai)
    if len(c.starts) > 2 and t >= c.L(2):
        a = appear(t, c.L(2))
        ph = (t - c.L(2)) * 0.9
        for i in range(n):                    # green checks travel along links
            j = (i + 1) % n; f = (ph + i * 0.13) % 1.0
            x = s(NET[i][0] + (NET[j][0] - NET[i][0]) * f); y = s(NET[i][1] + (NET[j][1] - NET[i][1]) * f)
            fade(im, lambda ov, x=x, y=y: ImageDraw.Draw(ov).ellipse((x - s(8), y - s(8), x + s(8), y + s(8)), fill=UP), a)
        def lb(ov):
            dd = ImageDraw.Draw(ov); f = F("Inter-Bold.otf", 26); txt = "NO SINGLE OWNER"
            w_ = dd.textlength(txt, font=f); pill(dd, (s(960) - w_ / 2 - s(18), s(530)), txt, f, BG, UP, (18, 9))
        fade(im, lb, appear(t, c.L(2) + 0.6))


def sc_chain(im, c, t):
    heading(im, c, t)
    nb = 5; bw, gap = 250, 90; x0 = 960 - (nb * bw + (nb - 1) * gap) / 2; y0 = 400
    end1 = c.L(2) if len(c.starts) > 2 else c.L(1) + 4
    hashes = ["a3f9…", "7c21…", "e04b…", "19d7…", "b6c0…"]
    tamper = len(c.starts) > 2 and t >= c.L(2) + 0.8
    for i in range(nb):
        ti = (i / nb) * max(0.8, end1 - 0.6)
        a = appear(t, ti)
        bad = tamper and i >= 1 and (t - c.L(2) - 0.8) > 0.25 * (i - 1)
        settle = len(c.starts) > 2 and t >= c.L(2) + 0.8 + 0.25 * nb + 1.4
        col = UP if settle else (DN if bad else BLUE)
        def blk(ov, i=i, col=col):
            dd = ImageDraw.Draw(ov); x = s(x0 + i * (bw + gap)); y = s(y0)
            card(dd, (x, y, x + s(bw), y + s(250)), col)
            dd.text((x + s(22), y + s(20)), f"BLOCK {i + 1}", font=F("Inter-Bold.otf", 24), fill=col)
            for k in range(3):
                dd.rounded_rectangle((x + s(22), y + s(70 + k * 44), x + s(bw - 22), y + s(100 + k * 44)), radius=s(8), fill=GRID)
                dd.text((x + s(34), y + s(73 + k * 44)), f"tx  {(i * 3 + k) * 37 % 90 + 10} → …", font=F("Inter-Medium.otf", 17), fill=MUTE)
            dd.text((x + s(22), y + s(210)), "#" + hashes[i], font=F("Inter-Medium.otf", 18), fill=TXT)
        fade(im, blk, a)
        if i > 0 and len(c.starts) > 1:
            al = appear(t, max(ti, c.L(1)) + 0.2)
            def lk(ov, i=i, col=col):
                dd = ImageDraw.Draw(ov); xa = s(x0 + i * (bw + gap) - gap); xb = s(x0 + i * (bw + gap)); y = s(y0 + 125)
                dd.line((xa, y, xb, y), fill=col, width=s(6))
                cx = (xa + xb) / 2; dd.rounded_rectangle((cx - s(16), y - s(10), cx + s(16), y + s(18)), radius=s(4), fill=col)
                dd.arc((cx - s(11), y - s(28), cx + s(11), y - s(2)), 180, 360, fill=col, width=s(5))
            fade(im, lk, al)
    if len(c.starts) > 2 and t >= c.L(2):
        lab = "Change one block?  Every block after it breaks." if not (t >= c.L(2) + 0.8 + 0.25 * nb + 1.4) else "Practically impossible to cheat"
        colr = DN if "Change" in lab else UP
        def tx(ov):
            dd = ImageDraw.Draw(ov); f = F("Inter-Bold.otf", 30); w_ = dd.textlength(lab, font=f)
            dd.text((s(960) - w_ / 2, s(700)), lab, font=f, fill=colr)
        fade(im, tx, appear(t, c.L(2) + 0.6))


def sc_number(im, c, t):
    heading(im, c, t)
    def coin(ov):
        dd = ImageDraw.Draw(ov); cx, cy, r = s(420), s(520), s(150)
        dd.ellipse((cx - r, cy - r, cx + r, cy + r), fill=(247, 147, 26)); dd.ellipse((cx - r + s(14), cy - r + s(14), cx + r - s(14), cy + r - s(14)), outline=(255, 200, 120), width=s(4))
        f = F("InterDisplay-Black.otf", 150); w_ = dd.textlength("B", font=f)
        dd.text((cx - w_ / 2, cy - s(98)), "B", font=f, fill=(255, 255, 255))
        for dx in (-s(22), s(14)):
            dd.rectangle((cx + dx, cy - s(120), cx + dx + s(10), cy - s(85)), fill=(255, 255, 255))
            dd.rectangle((cx + dx, cy + s(82), cx + dx + s(10), cy + s(118)), fill=(255, 255, 255))
    fade(im, coin, appear(t, 0.1))
    def yr(ov):
        dd = ImageDraw.Draw(ov); pill(dd, (s(700), s(360)), "SINCE 2009  ·  THE FIRST CRYPTOCURRENCY", F("Inter-SemiBold.otf", 22), ACC, (40, 33, 10), (16, 8))
    fade(im, yr, appear(t, 0.4))
    if len(c.starts) > 1:
        k = ease((t - c.L(1)) / 1.6); val = int(21_000_000 * k)
        def num(ov):
            dd = ImageDraw.Draw(ov)
            dd.text((s(700), s(430)), f"{val:,}", font=F("InterDisplay-Black.otf", 140), fill=TXT)
            dd.text((s(706), s(610)), c.sc.get("caption", ""), font=F("Inter-Regular.otf", 30), fill=MUTE)
        fade(im, num, appear(t, c.L(1)))
    if len(c.starts) > 2:
        def ps(ov):
            dd = ImageDraw.Draw(ov); pill(dd, (s(700), s(690)), "FIXED SUPPLY  ·  NO ONE CAN PRINT MORE", F("Inter-Bold.otf", 22), BG, UP, (16, 8))
        fade(im, ps, appear(t, c.L(2)))


def sc_points(im, c, t):
    heading(im, c, t)
    items = c.sc["items"]; lines = len(c.starts)
    il = c.sc.get("item_lines") or [i + (lines - len(items)) for i in range(len(items))]
    cur = c.active(t); hi = c.sc.get("highlight_line")
    for i, (tt, sub, colk) in enumerate(items):
        a = appear(t, c.L(il[i]))
        if a <= 0:
            continue
        col = COL.get(colk, BLUE); act = c.active(t) == il[i] or (hi is not None and cur == hi and i == len(items) - 1)
        y = s(250 + i * 190)
        def it(ov, tt=tt, sub=sub, col=col, act=act, y=y):
            dd = ImageDraw.Draw(ov); x = s(160) + int((1 - a) * s(30))
            dd.rounded_rectangle((x, y, s(1760), y + s(150)), radius=s(18), fill=PANEL if not act else tuple(int(PANEL[q] * 0.7 + col[q] * 0.12) for q in range(3)),
                                 outline=col + ((255,) if act else (90,)), width=s(2))
            dd.rounded_rectangle((x, y, x + s(12), y + s(150)), radius=s(6), fill=col)
            dd.text((x + s(50), y + s(26)), tt, font=F("Inter-Bold.otf", 40), fill=TXT if act else (200, 205, 215))
            dd.text((x + s(50), y + s(86)), sub, font=F("Inter-Regular.otf", 30), fill=col if act else MUTE)
        fade(im, it, a)


def sc_warning(im, c, t):
    a = appear(t, 0)
    def hd(ov):
        dd = ImageDraw.Draw(ov)
        pill(dd, (s(64), s(46)), f"LESSON {c.ep['number']:02d}  ·  {c.ep['level']}", F("Inter-SemiBold.otf", 19), ACC, (40, 33, 10))
        x, y = s(64), s(100); dd.polygon([(x + s(30), y), (x, y + s(52)), (x + s(60), y + s(52))], fill=DN)
        dd.text((x + s(23), y + s(10)), "!", font=F("Inter-Bold.otf", 34), fill=BG)
        dd.text((s(150), s(92)), c.sc.get("heading", ""), font=F("InterDisplay-Bold.otf", 50), fill=TXT)
    fade(im, hd, a)
    items = c.sc["items"]; off = len(c.starts) - len(items)
    for i, tx in enumerate(items):
        ai = appear(t, c.L(i + off))
        act = c.active(t) == i + off
        y = s(260 + i * 180)
        def it(ov, i=i, tx=tx, act=act, y=y, ai=ai):
            dd = ImageDraw.Draw(ov); x = s(160) + int((1 - ai) * s(30)); col = DN if act else (150, 70, 70)
            dd.rounded_rectangle((x, y, s(1760), y + s(140)), radius=s(18), fill=PANEL, outline=col, width=s(2))
            dd.ellipse((x + s(34), y + s(34), x + s(106), y + s(106)), fill=col)
            f = F("Inter-Bold.otf", 40); n = str(i + 1); dd.text((x + s(70) - dd.textlength(n, font=f) / 2, y + s(44)), n, font=f, fill=(255, 255, 255))
            dd.text((x + s(140), y + s(44)), tx, font=F("Inter-SemiBold.otf", 40), fill=TXT if act else (200, 205, 215))
        fade(im, it, ai)


CS = make_candles(60)


def sc_chart(im, c, t):
    heading(im, c, t)
    pb = (110, 230, 1690, 800)
    lo = min(x[2] for x in CS) - 3; hi = max(x[1] for x in CS) + 3
    Y = lambda v: s(pb[3] - (v - lo) / (hi - lo) * (pb[3] - pb[1]))
    step = (pb[2] - pb[0]) / len(CS); X = lambda i: s(pb[0] + step * i + step / 2); cw = s(step * 0.56)
    d = ImageDraw.Draw(im)
    d.rounded_rectangle((s(pb[0] - 30), s(pb[1] - 30), s(pb[2] + 30), s(pb[3] + 30)), radius=s(16), fill=PANEL)
    for k in range(1, 6):
        yy = s(pb[1] + (pb[3] - pb[1]) * k / 6); d.line((s(pb[0]), yy, s(pb[2]), yy), fill=GRID, width=1)
    total = c.t1 - c.t0
    N = min(len(CS), 4 + (len(CS) - 4) * min(1.0, t / max(1.0, total * 0.9)))
    k = int(N); f = N - k; live = list(CS[:k])
    if k < len(CS) and f > 0.02:
        o, h, l, cc = CS[k]; cv = o + (cc - o) * f + math.sin(t * 9) * 0.4 * (1 - f)
        live.append((o, max(o, cv), min(o, cv), cv))
    for i, (o, h, l, cc) in enumerate(live):
        col = UP if cc >= o else DN
        d.line((X(i), Y(h), X(i), Y(l)), fill=col, width=max(1, s(2.4)))
        tp, bt = sorted((Y(o), Y(cc))); d.rectangle((X(i) - cw / 2, tp, X(i) + cw / 2, max(bt, tp + 1)), fill=col)
    if live:
        cp = live[-1][3]; col = UP if live[-1][3] >= live[-1][0] else DN
        pill(d, (s(pb[2] + 40), Y(cp) - s(15)), f"{cp * 640:,.0f}", F("Inter-SemiBold.otf", 16), BG, col, (8, 4))
    d.text((s(pb[0]), s(pb[1] - 26)), "BTC / USDT  ·  example chart", font=F("Inter-SemiBold.otf", 18), fill=MUTE)
    clean = im.copy()
    li = c.sc.get("lens_line")
    if li is not None and li < len(c.starts):
        end = c.starts[li + 1] if li + 1 < len(c.starts) else total
        a = min(appear(t, c.L(li) + 0.2, 0.5), 1 - appear(t, end - 0.4, 0.4))
        tgt = max(range(min(len(live), 30)), key=lambda i: abs(CS[i][3] - CS[i][0]), default=None)
        if a > 0.01 and tgt is not None:
            px, py = X(tgt), (Y(CS[tgt][1]) + Y(CS[tgt][2])) / 2
            sw, sh = s(90), s(150); Z = 2.2
            crop = clean.crop((int(px - sw / 2), int(py - sh / 2), int(px + sw / 2), int(py + sh / 2)))
            LR = int(sh * Z / 2 * a)
            if LR > 4:
                big = crop.resize((int(sw * Z * a) or 1, int(sh * Z * a) or 1), Image.LANCZOS)
                lc = (s(1150), s(470))
                def conn(ov):
                    dd = ImageDraw.Draw(ov); r_ = sh / 2 + s(6)
                    for an in range(0, 360, 20):
                        dd.arc((px - r_, py - r_, px + r_, py + r_), an, an + 11, fill=ACC, width=s(3))
                    dd.line((px + r_, py, lc[0] - LR, lc[1]), fill=ACC, width=s(2))
                fade(im, conn, a)
                sh_ = Image.new("RGBA", (2 * LR + 60, 2 * LR + 60), (0, 0, 0, 0))
                ImageDraw.Draw(sh_).ellipse((24, 24, 2 * LR + 36, 2 * LR + 36), fill=(0, 0, 0, int(200 * a)))
                im.alpha_composite(sh_.filter(ImageFilter.GaussianBlur(10)), (int(lc[0] - LR - 30), int(lc[1] - LR - 30)))
                m = Image.new("L", big.size, 0)
                ImageDraw.Draw(m).ellipse((big.size[0] / 2 - LR, big.size[1] / 2 - LR, big.size[0] / 2 + LR, big.size[1] / 2 + LR), fill=int(255 * min(1, a * 1.3)))
                im.paste(big, (int(lc[0] - big.size[0] / 2), int(lc[1] - big.size[1] / 2)), m)
                glow(im, lc[0], lc[1], LR, ACC, a, 4)
                def co(ov):
                    dd = ImageDraw.Draw(ov); x, y = lc[0] + LR + s(30), lc[1] - s(110); lines = c.sc.get("lens_text", [])
                    hh = s(60 + 36 * len(lines))
                    dd.rounded_rectangle((x, y, x + s(400), y + hh), radius=s(14), fill=(12, 16, 26, 240), outline=ACC, width=s(2))
                    dd.text((x + s(20), y + s(16)), c.sc.get("lens_title", ""), font=F("Inter-SemiBold.otf", 24), fill=ACC)
                    for q, ln in enumerate(lines):
                        dd.text((x + s(20), y + s(56) + q * s(36)), ln, font=F("Inter-Regular.otf", 22), fill=TXT)
                fade(im, co, appear(t, c.L(li) + 0.7))
    if len(c.starts) > 2:
        end = c.starts[3] if len(c.starts) > 3 else total
        a = min(appear(t, c.L(2)), 1 - appear(t, end - 0.3, 0.3))
        def gr(ov):
            dd = ImageDraw.Draw(ov)
            pill(dd, (s(160), s(260)), "▲ GREEN = closed higher", F("Inter-Bold.otf", 26), BG, UP, (16, 8))
            pill(dd, (s(560), s(260)), "▼ RED = closed lower", F("Inter-Bold.otf", 26), (255, 255, 255), DN, (16, 8))
        fade(im, gr, a)
    if len(c.starts) > 3:
        a = appear(t, c.L(3))
        def oc(ov):
            dd = ImageDraw.Draw(ov)
            pill(dd, (s(160), s(260)), "▲ OPPORTUNITY", F("Inter-Bold.otf", 30), BG, UP, (18, 9))
            pill(dd, (s(540), s(260)), "▼ DANGER", F("Inter-Bold.otf", 30), (255, 255, 255), DN, (18, 9))
        fade(im, oc, a)


def sc_outro(im, c, t):
    def nx(ov):
        dd = ImageDraw.Draw(ov)
        dd.text((s(160), s(220)), "NEXT LESSON", font=F("Inter-SemiBold.otf", 26), fill=ACC)
        for q, ln in enumerate(wrap(dd, c.sc.get("next", ""), F("InterDisplay-Bold.otf", 64), s(1600))):
            dd.text((s(160), s(270 + q * 80)), ln, font=F("InterDisplay-Bold.otf", 64), fill=TXT)
    fade(im, nx, appear(t, 0.1))
    if len(c.starts) > 1:
        a = appear(t, c.L(1)); pulse = 1 + 0.04 * math.sin(t * 6)
        def sb(ov):
            dd = ImageDraw.Draw(ov); x, y, w_, h_ = s(160), s(520), s(360) * pulse, s(96) * pulse
            dd.rounded_rectangle((x, y, x + w_, y + h_), radius=s(16), fill=(230, 33, 23))
            dd.polygon([(x + s(40), y + s(28)), (x + s(40), y + s(68)), (x + s(74), y + s(48))], fill=(255, 255, 255))
            dd.text((x + s(96), y + s(26)), "SUBSCRIBE", font=F("Inter-Bold.otf", 38), fill=(255, 255, 255))
            dd.text((s(580), s(530)), "@CryptoAIAcademyy", font=F("Inter-SemiBold.otf", 32), fill=TXT)
            dd.text((s(580), s(578)), "cryptoai-main-site.onrender.com  ·  t.me/CryptoAI_FARSI  ·  t.me/CryptoAI_World", font=F("Inter-Regular.otf", 22), fill=MUTE)
        fade(im, sb, a)


RENDER = {"title": sc_title, "flow": sc_flow, "network": sc_network, "chain": sc_chain, "number": sc_number,
          "points": sc_points, "warning": sc_warning, "chart": sc_chart, "outro": sc_outro}


# ------------------------------------------------------------------ chrome: brand, Persian subtitle, chapter bar
def chrome(im, ep, timeline, t, cur_scene):
    d = ImageDraw.Draw(im)
    br = "CryptoAI Academy"; fb = F("Inter-SemiBold.otf", 22); bw = d.textlength(br, font=fb)
    d.ellipse((s(1856) - bw - s(34), s(54), s(1856) - bw - s(18), s(70)), fill=BLUE); d.text((s(1856) - bw, s(46)), br, font=fb, fill=TXT)
    # Persian subtitle of the line being spoken
    for sc in timeline:
        for ln in sc["lines"]:
            if ln["t0"] - 0.05 <= t < ln["t1"] + 0.25:
                a = min(appear(t, ln["t0"] - 0.05, 0.2), 1 - appear(t, ln["t1"] + 0.05, 0.2))
                def sb(ov, txt=ln["fa"]):
                    dd = ImageDraw.Draw(ov); fs = FA(36); sw = dd.textlength(txt, font=fs, **FAKW)
                    if sw > s(1700):
                        fs = FA(30); sw = dd.textlength(txt, font=fs, **FAKW)
                    sy = s(H / K - 168)
                    dd.rounded_rectangle(((W - sw) / 2 - s(26), sy - s(12), (W + sw) / 2 + s(26), sy + s(62)), radius=s(10), fill=(0, 0, 0, 185))
                    dd.text((W / 2, sy), txt, font=fs, fill=TXT, anchor="ma", **FAKW)
                fade(im, sb, a)
    # chapter progress
    n = len(timeline); cw = (s(1792)) / n; y0 = s(1080 - 62)
    for k, sc in enumerate(timeline):
        xa = s(64) + cw * k + s(3); xb = s(64) + cw * (k + 1) - s(3)
        d.rounded_rectangle((xa, y0, xb, y0 + s(6)), radius=s(3), fill=GRID)
        fr = max(0.0, min(1.0, (t - sc["t0"]) / max(0.1, sc["t1"] - sc["t0"])))
        if fr > 0:
            d.rounded_rectangle((xa, y0, xa + (xb - xa) * fr, y0 + s(6)), radius=s(3), fill=BLUE)
        lab = sc.get("chapter", "")
        f = F("Inter-Medium.otf", 15)
        while d.textlength(lab, font=f) > (xb - xa) and len(lab) > 3:
            lab = lab[:-2] + "…" if not lab.endswith("…") else lab[:-2] + "…"
        d.text((xa, y0 + s(12)), lab, font=f, fill=TXT if k == cur_scene else MUTE)


def frame(ep, timeline, t):
    im = Image.new("RGBA", (W, H), BG + (255,))
    cur = 0
    for i, sc in enumerate(timeline):
        if t >= sc["t0"]:
            cur = i
    sc = timeline[cur]
    tl = t - sc["t0"]
    starts = [ln["t0"] - sc["t0"] for ln in sc["lines"]]
    ends = [ln["t1"] - sc["t0"] for ln in sc["lines"]]
    ctx = Ctx(ep, sc["src"], cur, starts, ends, sc["t0"], sc["t1"])
    RENDER[sc["src"]["type"]](im, ctx, tl)
    # scene cross-fade from black at the start of each scene
    if tl < 0.35 and cur > 0:
        k = 1 - tl / 0.35
        im.alpha_composite(Image.new("RGBA", (W, H), BG + (int(255 * k),)))
    chrome(im, ep, timeline, t, cur)
    return im.convert("RGB")


# ------------------------------------------------------------------ audio + timeline
def probe_dur(path):
    r = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "default=nw=1:nk=1", str(path)],
                       capture_output=True, text=True, check=True)
    return float(r.stdout.strip())


VOICES = [VOICE, "en-US-AndrewNeural", "en-US-GuyNeural", "en-US-EmmaMultilingualNeural", "en-US-AriaNeural"]
_voice_ok: list = []


async def _tts(text, path):
    import edge_tts
    order = _voice_ok[:1] + [v for v in VOICES if v not in _voice_ok[:1]]
    last = None
    for v in order:
        for rate in ("-4%", None):
            try:
                kw = {"rate": rate} if rate else {}
                await edge_tts.Communicate(text, v, **kw).save(str(path))
                if path.stat().st_size > 1000:
                    if not _voice_ok:
                        _voice_ok.append(v); print("voice:", v, flush=True)
                    return
            except Exception as e:
                last = e
    raise RuntimeError(f"no TTS voice worked: {last}")


def build_audio(ep, work: Path, silent: bool):
    LEAD, GAP, SGAP, TAIL = 0.6, 0.35, 0.8, 1.6
    t = LEAD; timeline = []; parts = []
    for si, sc in enumerate(ep["scenes"]):
        t0 = t; lines = []
        for li, ln in enumerate(sc["lines"]):
            wav = work / f"s{si:02d}_{li:02d}.wav"
            if silent:
                dur = max(1.4, len(ln["en"].split()) / 2.55)
                subprocess.run([FFMPEG, "-v", "error", "-y", "-f", "lavfi", "-i", "anullsrc=r=24000:cl=mono", "-t", f"{dur:.3f}", str(wav)], check=True)
            else:
                mp3 = work / f"s{si:02d}_{li:02d}.mp3"
                for attempt in range(3):
                    try:
                        asyncio.run(_tts(ln["en"], mp3)); break
                    except Exception:
                        if attempt == 2:
                            raise
                        import time; time.sleep(5)
                subprocess.run([FFMPEG, "-v", "error", "-y", "-i", str(mp3), "-ar", "24000", "-ac", "1", str(wav)], check=True)
                dur = probe_dur(wav)
            lines.append({"en": ln["en"], "fa": ln["fa"], "t0": t, "t1": t + dur})
            parts.append((t, wav)); t += dur + GAP
        t += SGAP - GAP
        timeline.append({"t0": t0, "t1": t, "lines": lines, "src": sc, "chapter": sc.get("chapter", "")})
    total = t + TAIL
    timeline[-1]["t1"] = total
    # place every line at its exact start time on one silent track
    inputs, filt = [], []
    for i, (st, wav) in enumerate(parts):
        inputs += ["-i", str(wav)]; filt.append(f"[{i + 1}:a]adelay={int(st * 1000)}|{int(st * 1000)}[a{i}]")
    mix = "".join(f"[a{i}]" for i in range(len(parts)))
    filt.append(f"[0:a]{mix}amix=inputs={len(parts) + 1}:normalize=0,atrim=0:{total:.3f}[out]")
    audio = work / "voice.m4a"
    subprocess.run([FFMPEG, "-v", "error", "-y", "-f", "lavfi", "-t", f"{total:.3f}", "-i", "anullsrc=r=24000:cl=mono", *inputs,
                    "-filter_complex", ";".join(filt), "-map", "[out]", "-c:a", "aac", "-b:a", "48k", "-ac", "1", str(audio)], check=True)
    return timeline, total, audio


def encode(ep, timeline, total, audio, out_mp4: Path, max_bytes=4_600_000):
    nfr = int(total * FPS)
    for vb in (230, 170, 120):
        p = subprocess.Popen([FFMPEG, "-v", "error", "-y", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-",
                              "-i", str(audio), "-map", "0:v", "-map", "1:a", "-c:v", "libx264", "-preset", "veryfast", "-tune", "animation",
                              "-b:v", f"{vb}k", "-maxrate", f"{int(vb * 1.4)}k", "-bufsize", f"{vb * 3}k", "-pix_fmt", "yuv420p",
                              "-c:a", "copy", "-shortest", "-movflags", "+faststart", str(out_mp4)], stdin=subprocess.PIPE)
        for i in range(nfr):
            p.stdin.write(frame(ep, timeline, i / FPS).tobytes())
        p.stdin.close(); p.wait()
        if p.returncode != 0:
            raise RuntimeError("ffmpeg failed")
        if out_mp4.stat().st_size <= max_bytes:
            return
        print(f"  {out_mp4.name}: {out_mp4.stat().st_size} bytes > limit, re-encoding smaller", flush=True)


def make_short(ep, timeline, long_mp4: Path, out_mp4: Path):
    idx = ep.get("short_scenes") or [1]
    a, b = timeline[idx[0]]["t0"], min(timeline[idx[-1]]["t1"], timeline[idx[0]]["t0"] + 58)
    top = Image.new("RGBA", (1080, 1920), BG + (255,)); d = ImageDraw.Draw(top)
    hook = ep.get("short_hook", ep["title"])
    f = ImageFont.truetype(str(FONTS / "InterDisplay-Black.otf"), 84)
    lines = wrap(d, hook, f, 960)
    for q, ln in enumerate(lines):
        d.text((540, 300 + q * 100), ln, font=f, fill=TXT, anchor="ma")
    ffa = ImageFont.truetype(str(FONTS / "Vazirmatn-Bold.ttf"), 64, layout_engine=ImageFont.Layout.RAQM if RAQM else ImageFont.Layout.BASIC)
    d.text((540, 320 + len(lines) * 100), ep.get("short_hook_fa", ""), font=ffa, fill=ACC, anchor="ma", **FAKW)
    fp = ImageFont.truetype(str(FONTS / "Inter-SemiBold.otf"), 34)
    lab = f"LESSON {ep['number']:02d}  ·  CRYPTOAI ACADEMY"; tw = d.textlength(lab, font=fp)
    d.rounded_rectangle((540 - tw / 2 - 26, 180, 540 + tw / 2 + 26, 236), radius=28, fill=(40, 33, 10)); d.text((540, 190), lab, font=fp, fill=ACC, anchor="ma")
    fb = ImageFont.truetype(str(FONTS / "Inter-Bold.otf"), 44)
    d.rounded_rectangle((170, 1500, 910, 1600), radius=24, fill=(230, 33, 23)); d.text((540, 1522), "Full lesson on the channel  ▶", font=fb, fill=(255, 255, 255), anchor="ma")
    d.text((540, 1640), "@CryptoAIAcademyy", font=ImageFont.truetype(str(FONTS / "Inter-SemiBold.otf"), 40), fill=TXT, anchor="ma")
    d.text((540, 1700), "Education, not financial advice", font=ImageFont.truetype(str(FONTS / "Inter-Regular.otf"), 30), fill=MUTE, anchor="ma")
    with tempfile.TemporaryDirectory() as td:
        bgp = Path(td) / "bg.png"; top.convert("RGB").save(bgp)
        subprocess.run([FFMPEG, "-v", "error", "-y", "-loop", "1", "-i", str(bgp), "-ss", f"{a:.3f}", "-to", f"{b:.3f}", "-i", str(long_mp4),
                        "-filter_complex", "[1:v]crop=1120:660:80:0,scale=1080:636,setsar=1[v];[0:v][v]overlay=0:600:shortest=1,fps=24,format=yuv420p[o]",
                        "-map", "[o]", "-map", "1:a", "-c:v", "libx264", "-preset", "veryfast", "-crf", "28", "-maxrate", "900k", "-bufsize", "1800k",
                        "-c:a", "aac", "-b:a", "64k", "-shortest", "-movflags", "+faststart", str(out_mp4)], check=True)


def fmt_ts(x):
    x = int(x); return f"{x // 60}:{x % 60:02d}"


def main():
    ep_id = sys.argv[1]; silent = "--silent" in sys.argv
    if not RAQM and not silent:
        sys.exit("Persian text shaping (raqm) is missing: refusing to render broken subtitles.")
    ep = json.loads((ROOT / "episodes" / f"{ep_id}.json").read_text())
    OUT.mkdir(exist_ok=True)
    with tempfile.TemporaryDirectory() as td:
        timeline, total, audio = build_audio(ep, Path(td), silent)
        long_mp4 = OUT / f"{ep_id}-long.mp4"; short_mp4 = OUT / f"{ep_id}-short.mp4"
        print(f"rendering {ep_id}: {total:.1f}s", flush=True)
        encode(ep, timeline, total, audio, long_mp4)
        make_short(ep, timeline, long_mp4, short_mp4)
    chapters = "\n".join(f"{fmt_ts(sc['t0'] if i else 0)} {sc['chapter']}" for i, sc in enumerate(timeline))
    meta = {"id": ep_id, "duration": round(total, 1), "chapters": chapters,
            "long_bytes": long_mp4.stat().st_size, "short_bytes": short_mp4.stat().st_size}
    (OUT / f"{ep_id}-meta.json").write_text(json.dumps(meta, ensure_ascii=False, indent=1))
    print(json.dumps(meta, ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main()
