#!/usr/bin/env python3
"""Draws the SewarOS 98 images for my GitHub profile README.

    python -m venv .venv && .venv/bin/pip install -r requirements.txt
    .venv/bin/python build.py

A README image can't run JavaScript, so everything is SVG with CSS animation.
The pixel font (VT323, SIL Open Font License) is subset and embedded, because
an image on GitHub can't load fonts from outside itself.
"""
import base64
import io
import json
import math
import os
import random
import subprocess
import textwrap
import urllib.request
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from xml.sax.saxutils import escape

from fontTools import subset
from fontTools.ttLib import TTFont

ROOT = Path(__file__).resolve().parent
ASSETS = ROOT / "assets"
DATA = ROOT / "data" / "activity.json"
FONT = ROOT / ".cache" / "VT323-Regular.ttf"
FONT_URL = "https://github.com/google/fonts/raw/main/ofl/vt323/VT323-Regular.ttf"
USER, YEAR = "SewarRihani", 2026
SITE = "https://sewarrihani.github.io/SewarRihani/"  # the clickable SewarOS 98 (GitHub Pages, docs/)

ADV = 0.4  # VT323 is monospaced: every glyph is 0.4 em wide
B = 1.5    # bevel line width

INK, SOFT, LILAC, MINT, WHITE = "#efe8ff", "#b8aadb", "#c9a8ff", "#7ef0c0", "#ffffff"
FACE, HI, HI2, SH, SH2, WELL, SEL = "#2a2042", "#7a62b8", "#4a3a78", "#07040d", "#171026", "#120c1f", "#7c4dff"
EMOJI_FONTS = '"Apple Color Emoji","Segoe UI Emoji","Noto Color Emoji",sans-serif'

# ───────────────────────────── content ─────────────────────────────

PROJECTS = [
    dict(key="care", emoji="🐾", name="CareTail Echo", kind="Vet labelling tool · graduation project",
         short="Vets label 1,201 cat and dog sounds as Positive, Negative or Unknown.",
         chips=["Streamlit", "pandas", "1,201 clips"], status=["1,201 clips", "3 labels", "saves to CSV"],
         repo="https://github.com/SewarRihani/OnlineLabelingApp"),
    dict(key="ocd", emoji="🧹", name="OCDAgent", kind="Mac organiser · Python",
         short="Tidies a Mac into colour-coded folders and never deletes on its own.",
         chips=["Python", "launchd", "Finder tags"], status=["93 moved", "0 deleted", "every move undoable"],
         soon="Public version coming soon"),
    dict(key="chef", emoji="🍳", name="Chefmates", kind="Two-player co-op pixel game",
         short="A two-player pixel game about the four parts an AI agent needs.",
         chips=["TypeScript", "React", "own canvas engine"], status=["2 players", "4 parts", "runs offline"],
         soon="Code going public soon"),
    dict(key="bday", emoji="🎂", name="Birthday Chronicle", kind="Interactive birthday website",
         short="A birthday site with a 3D cake, honey pots, a quiz and music.",
         chips=["React", "Three.js", "Framer Motion"], status=["3D cake", "honey pots", "quiz + music"],
         soon="Public version coming soon"),
]

# the CV window: one calm page, no tabs
CV = dict(
    name="SEWAR ALRIHANI",
    title="AI Engineer · Amman, Jordan",
    kpis=[("1 of 20", "fellows from 1,000+ applicants"), ("2", "AI engineering roles"), ("AR+EN", "bilingual AI")],
    rows=[("NOW", "AI Engineer (Contract)", "9XAI · HTU · 2026 – now"),
          ("BEFORE", "AI/ML Engineer Intern", "Acabes International · 2025"),
          ("STUDIED", "B.Sc. Artificial Intelligence", "University of Jordan · 2022 – 2026")],
    cta="> Open to AI engineering roles",
)

# ───────────────────────────── drawing kit ─────────────────────────────


def f(v):
    return f"{v:.2f}".rstrip("0").rstrip(".")


def wrap(s, width, size):
    return textwrap.wrap(s, max(1, int(width // (ADV * size))))


def rect(x, y, w, h, fill, extra=""):
    return f'<rect x="{f(x)}" y="{f(y)}" width="{f(w)}" height="{f(h)}" fill="{fill}"{extra}/>'


def raised(x, y, w, h, face=FACE):
    return (rect(x, y, w, h, SH) + rect(x, y, w - B, h - B, HI) + rect(x + B, y + B, w - 2 * B, h - 2 * B, SH2)
            + rect(x + B, y + B, w - 3 * B, h - 3 * B, HI2) + rect(x + 2 * B, y + 2 * B, w - 4 * B, h - 4 * B, face))


def sunken(x, y, w, h, fill=WELL):
    return (rect(x, y, w, h, HI2) + rect(x, y, w - B, h - B, SH2) + rect(x + B, y + B, w - 2 * B, h - 2 * B, HI)
            + rect(x + B, y + B, w - 3 * B, h - 3 * B, SH) + rect(x + 2 * B, y + 2 * B, w - 4 * B, h - 4 * B, fill))


def groove(x, y, w, h, fill=FACE):
    return rect(x, y, w, h, HI2) + rect(x, y, w - 1, h - 1, SH2) + rect(x + 1, y + 1, w - 2, h - 2, fill)


class SVG:
    """One image: collects shapes, CSS, defs and the characters the embedded font must cover."""

    def __init__(self, w, h, title):
        self.w, self.h, self.title = w, h, title
        self.defs, self.css, self.chars = [], [], set()

    def text(self, x, y, s, size, fill=INK, anchor="start", cls="", attrs=""):
        self.chars.update(s)
        a = f' text-anchor="{anchor}"' if anchor != "start" else ""
        c = f' class="{cls}"' if cls else ""
        return f'<text x="{f(x)}" y="{f(y)}" font-size="{f(size)}" fill="{fill}"{a}{c}{attrs}>{escape(s)}</text>'

    def emoji(self, x, y, e, size, cls=""):
        return (f'<text class="e{" " + cls if cls else ""}" x="{f(x)}" y="{f(y)}" font-size="{f(size)}" '
                f'text-anchor="middle" dominant-baseline="central">{e}</text>')

    def toggle(self, name, period, windows, delay=0):
        """Class `name` is shown (opacity 1) only inside the (start, end) windows of a looping period."""
        start = 1 if any(a <= 0 < b for a, b in windows) else 0
        changes = sorted({(a, 1) for a, _ in windows if a > 0} | {(b, 0) for _, b in windows if b < period})
        last = changes[-1][1] if changes else start
        frames = [f"0%{{opacity:{start}}}"] + [f"{f(t / period * 100)}%{{opacity:{v}}}" for t, v in changes]
        frames.append(f"100%{{opacity:{last}}}")
        self.css.append(f"@keyframes {name}{{{''.join(frames)}}}"
                        f".{name}{{animation:{name} {f(period)}s steps(1,end) {f(delay)}s infinite}}")

    def art_toggle(self, name, windows):
        self.toggle(name, ART, windows)

    def render(self, body):
        css = "\n".join(self.css)
        return (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {self.w} {self.h}" width="{self.w}" '
                f'height="{self.h}" role="img" aria-labelledby="t">\n<title id="t">{escape(self.title)}</title>\n'
                f'<style>\n@font-face{{font-family:"VT323";src:url(data:font/woff;base64,{font_b64(self.chars)}) '
                f'format("woff")}}\ntext{{font-family:"VT323",ui-monospace,monospace}}\n.e{{font-family:{EMOJI_FONTS}}}\n'
                f'{css}\n@media (prefers-reduced-motion:reduce){{*{{animation:none!important}}.cur{{display:none}}}}\n'
                f'</style>\n<defs>{"".join(self.defs)}</defs>\n{body}\n</svg>\n')


def font_b64(chars):
    if not FONT.exists():
        FONT.parent.mkdir(parents=True, exist_ok=True)
        urllib.request.urlretrieve(FONT_URL, FONT)
    tt = TTFont(FONT, recalcTimestamp=False)  # same bytes every build, so git only sees real changes
    cmap = tt.getBestCmap()
    missing = sorted({c for c in chars if ord(c) not in cmap and not c.isspace()})
    if missing:
        raise SystemExit(f"VT323 has no glyph for: {' '.join(missing)}")
    opts = subset.Options()
    opts.flavor, opts.name_IDs, opts.layout_features = "woff", ["*"], []  # keep the licence in the name table
    sub = subset.Subsetter(opts)
    sub.populate(unicodes={ord(c) for c in chars | {" "}})
    sub.subset(tt)
    buf = io.BytesIO()
    tt.flavor = "woff"
    tt.save(buf)
    return base64.b64encode(buf.getvalue()).decode()


def window(s, x, y, w, h, emoji, title, ctl="_□×"):
    """A bevelled 90s window. Returns its SVG and the centre of each title-bar button."""
    out = [raised(x, y, w, h), rect(x + 4, y + 4, w - 8, 26, "url(#tb)")]
    out.append(s.emoji(x + 17, y + 17, emoji, 15))
    out.append(s.text(x + 30, y + 24, title, 19, WHITE))
    at = {}
    for i, g in enumerate(ctl):
        bx = x + w - 6 - (len(ctl) - i) * 22
        out.append(raised(bx, y + 8, 20, 18))
        if g == "□":
            out.append(f'<path d="M{f(bx + 5)} {f(y + 11.5)}h10v10h-10z M{f(bx + 5)} {f(y + 13)}h10" '
                       f'stroke="{INK}" stroke-width="1.5" fill="none"/>')
        else:
            out.append(s.text(bx + 10, y + (23 if g == "×" else 21), g, 20 if g == "×" else 17, INK, "middle"))
        at[g] = (bx + 10, y + 17)
    return "".join(out), at


def status_bar(s, x, y, w, cells):
    out, cw = [], w / len(cells)
    for i, c in enumerate(cells):
        out.append(groove(x + i * cw, y, cw - 3, 21) + s.text(x + i * cw + 7, y + 16, c, 15, SOFT))
    return "".join(out)


# ───────────────────────────── project pictures ─────────────────────────────


ART = 6  # each project picture loops in 6 seconds, the time each project stays on screen


def art(s, x, y, w, h, key):
    """Draws a project's picture at (x, y)."""
    s.defs.append(f'<clipPath id="clip-{key}"><rect width="{f(w)}" height="{f(h)}"/></clipPath>')
    inner = {"care": art_care, "ocd": art_ocd, "chef": art_chef, "bday": art_bday}[key](s, w, h)
    return f'<g transform="translate({f(x)},{f(y)})" clip-path="url(#clip-{key})">{inner}</g>'


def art_care(s, w, h):
    """An oscilloscope plays a cat clip, then the vet presses Positive."""
    green, r, out = "#3cff78", random.Random(317), [rect(0, 0, w, h, "#041a0b")]
    grid = [f"M{g} 0V{f(h)}" for g in range(16, int(w), 16)] + [f"M0 {g}H{f(w)}" for g in range(16, int(h), 16)]
    out.append(f'<path d="{" ".join(grid)}" stroke="{green}" stroke-opacity=".13" stroke-width="1"/>')
    out.append(s.text(12, 23, "PLAYING cat_0318.wav", 16, green))
    out.append(s.text(w - 12, 23, "CAT · CLIP 318 OF 1,201", 16, green, "end"))
    top, bot = 36, h - 56
    mid, amp, n = (top + bot) / 2, (bot - top) / 2, int((w - 24) / 7.5)
    bw, bars = (w - 24) / n, []
    for i in range(n):
        hh = amp * (0.1 + 0.9 * r.random() * abs(math.sin(i / 5)))
        bars.append(f"M{f(12 + i * bw + bw * .2)} {f(mid - hh)}h{f(bw * .6)}v{f(2 * hh)}h{f(-bw * .6)}z")
    out.append(f'<path d="{"".join(bars)}" fill="{green}"/>')
    # the played part: a lilac wash that grows behind a playhead
    played = f(3.6 / ART * 100)  # the clip plays for 3.6 s
    s.css.append(f"@keyframes care-grow{{0%{{transform:scaleX(0)}}{played}%,100%{{transform:scaleX(1)}}}}"
                 f".care-grow{{transform-box:fill-box;transform-origin:0 50%;animation:care-grow {ART}s linear infinite}}"
                 f"@keyframes care-head{{0%{{transform:translateX(0)}}{played}%,100%{{transform:translateX({f(w - 24)}px)}}}}"
                 f".care-head{{animation:care-head {ART}s linear infinite}}")
    out.append(f'<rect class="care-grow" x="12" y="{top}" width="{f(w - 24)}" height="{f(bot - top)}" fill="#c8a8ff" opacity=".28"/>')
    out.append(f'<rect class="care-head" x="11" y="{top - 4}" width="2" height="{f(bot - top + 8)}" fill="#c8a8ff" opacity=".9"/>')
    s.art_toggle("care-press", [(3.75, ART)])
    bx = 12
    for i, (e, lab) in enumerate([("😊", "Positive"), ("😠", "Negative"), ("❓", "Unknown")]):
        bw_ = 30 + len(lab) * 6.8 + 12
        out.append(raised(bx, h - 44, bw_, 30) + s.emoji(bx + 16, h - 29, e, 15) + s.text(bx + 29, h - 23, lab, 17))
        if i == 0:
            out.append(f'<g class="care-press">{sunken(bx, h - 44, bw_, 30, "#3fc26a")}'
                       f'{s.emoji(bx + 17, h - 28, e, 15)}{s.text(bx + 30, h - 22, lab, 17, "#06170d")}</g>')
        bx += bw_ + 8
    if w > 600:
        out.append(s.text(w - 12, h - 23, "progress saved to CSV", 16, green, "end"))
    return "".join(out)


def art_ocd(s, w, h):
    """Folders pop into place one by one, each with its colour and emoji. Nothing is deleted."""
    out = [rect(0, 0, w, h, WELL), s.text(14, 24, "Tidying Desktop and Downloads...", 16, SOFT)]
    folders = [("💼", "Work", "#3b82f6"), ("💜", "Personal", "#a855f7"), ("💻", "Projects", "#8e8e93"),
               ("📚", "Study", "#34c759"), ("📄", "Career", "#ff9500"), ("🖼️", "Photos", "#ff3b30"),
               ("🌄", "Wallpapers", "#34c759"), ("📦", "Archive", "#8e8e93")]
    cols = 8 if w > 600 else 4
    rows = len(folders) // cols
    top, cw = 34, (w - 28) / cols
    ch = (h - top - 40) / rows
    fh = min(ch - 24, 64)
    fw = fh / 0.72
    for i, (e, lab, col) in enumerate(folders):
        cx, fy = 14 + cw * (i % cols + .5), top + ch * (i // cols) + (ch - fh - 20) / 2
        x0 = cx - fw / 2
        s.art_toggle(f"ocd-f{i}", [(0.3 + 0.28 * i, ART - .2)])
        out.append(f'<g class="ocd-f{i}">'
                   f'<path d="M{f(x0)} {f(fy + fh * .16)}V{f(fy + 3)}q0-3 3-3h{f(fw * .32)}l{f(fh * .12)} {f(fh * .16)}z" fill="{col}" opacity=".7"/>'
                   f'{rect(x0, fy + fh * .14, fw, fh * .86, col, " rx=\"3\"")}'
                   f'{s.emoji(cx, fy + fh * .58, e, fh * .42)}{s.text(cx, fy + fh + 17, lab, 15, INK, "middle")}</g>')
    s.art_toggle("ocd-stamp", [(2.9, ART - .2)])
    label = "93 MOVED · 0 DELETED"
    sw = len(label) * 7.2 + 18
    out.append(f'<g class="ocd-stamp">{rect(w - 12 - sw, h - 36, sw, 26, "#0b7a2e")}'
               f'{s.text(w - 12 - sw / 2, h - 17, label, 18, WHITE, "middle")}</g>')
    if w > 600:
        out.append(s.text(14, h - 17, "Duplicates are proven byte by byte before anything goes.", 16, SOFT))
    return "".join(out)


def art_chef(s, w, h):
    """Salt and Pepper hop through the kitchen; the plug (knowledge) is the first of the mixer's four parts."""
    gy = h - 26
    s.defs.append('<linearGradient id="chef-sky" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#2b1f55"/>'
                  '<stop offset=".7" stop-color="#573a8f"/><stop offset="1" stop-color="#7d5cc4"/></linearGradient>'
                  '<pattern id="chef-brick" width="24" height="24" patternUnits="userSpaceOnUse">'
                  '<rect width="12" height="24" fill="#c47a3a"/><rect x="12" width="12" height="24" fill="#a8622c"/></pattern>'
                  '<radialGradient id="chef-glow"><stop offset="0" stop-color="#ffd54a" stop-opacity=".55"/>'
                  '<stop offset="1" stop-color="#ffd54a" stop-opacity="0"/></radialGradient>')
    r = random.Random(7)
    out = [rect(0, 0, w, h, "url(#chef-sky)")]
    out += [rect(r.uniform(0, w), r.uniform(40, h * .55), 2, 2, WHITE, ' opacity=".45"') for _ in range(int(w / 30))]
    out.append(rect(0, gy, w, 26, "url(#chef-brick)") + rect(0, gy - 4, w, 4, "#6fcf4c"))
    for fx, fy, fw in [(.16, 60, .13), (.38, 90, .12), (.60, 64, .12)]:
        out.append(rect(fx * w, h - fy, fw * w, 10, "url(#chef-brick)") + rect(fx * w, h - fy - 3, fw * w, 3, "#6fcf4c"))
    s.css.append("@keyframes chef-float{50%{transform:translateY(-6px)}}.chef-float{animation:chef-float 2.4s ease-in-out infinite}"
                 "@keyframes chef-hop{50%{transform:translateY(-12px)}}.chef-hop{animation:chef-hop 1.6s steps(2) infinite}"
                 ".chef-hop2{animation:chef-hop 1.6s steps(2) .8s infinite}"
                 "@keyframes chef-blink{50%{opacity:0}}.chef-blink{animation:chef-blink 1s steps(1) infinite}")
    # the plug waits on the middle platform until it's picked up
    px, py = (.38 + .06) * w, h - 90 - 22
    s.art_toggle("chef-plug", [(0, 2.0)])
    out.append(f'<g class="chef-plug"><g class="chef-float"><circle cx="{f(px)}" cy="{f(py)}" r="22" fill="url(#chef-glow)"/>'
               f'{s.emoji(px, py, "🔌", 22)}</g></g>')
    for i, (body, dots, cls) in enumerate([("#f4f1ea", "#3a3a44", "chef-hop"), ("#2b2b35", "#d9d6cf", "chef-hop2")]):
        sx = .05 * w + i * 26
        out.append(f'<g class="{cls}">{rect(sx, gy - 30, 18, 30, body, " rx=\"6\"")}'
                   + "".join(f'<circle cx="{f(sx + 5 + k * 4)}" cy="{f(gy - 24)}" r="1.1" fill="{dots}"/>' for k in range(3))
                   + "</g>")
    # the runaway mixer, still missing its parts
    mx = .84 * w
    out.append(rect(mx - 36, gy - 10, 72, 10, "#d1d5db") + rect(mx + 18, gy - 62, 14, 52, "#d1d5db")
               + rect(mx - 32, gy - 76, 66, 22, "#e5e7eb", ' rx="10"')
               + f'<path d="M{f(mx - 30)} {f(gy - 36)}h44q0 26-22 26q-22 0-22-26z" fill="#9ca3af"/>')
    out.append(s.text(mx, gy - 86, "?", 28, "#ffd54a", "middle", "chef-blink"))
    # parts found
    s.art_toggle("chef-found", [(2.0, ART)])
    s.art_toggle("chef-none", [(0, 2.0)])
    x = 12
    for part in ["GOAL", "KNOWLEDGE", "TOOL", "RULES"]:
        pw = len(part) * 6 + 16
        out.append(rect(x, 10, pw, 24, "#1d1533", f' stroke="{LILAC}" stroke-opacity=".5"')
                   + s.text(x + pw / 2, 27, part, 15, SOFT, "middle"))
        if part == "KNOWLEDGE":
            out.append(f'<g class="chef-found">{rect(x, 10, pw, 24, "#ffd54a")}{s.text(x + pw / 2, 27, part, 15, "#1b1405", "middle")}</g>')
        x += pw + 6
    out.append(f'<g class="chef-none" opacity="0">{s.text(w - 12, 28, "PARTS 0/4", 18, WHITE, "end")}</g>'
               f'<g class="chef-found">{s.text(w - 12, 28, "PARTS 1/4", 18, WHITE, "end")}</g>')
    return "".join(out)


def art_bday(s, w, h):
    """A cake whose candles blow out, a honey pot to open, and photo spots left as placeholders."""
    s.defs.append('<linearGradient id="bday-bg" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stop-color="#ffe3f1"/>'
                  '<stop offset=".55" stop-color="#e9dcff"/><stop offset="1" stop-color="#d7f1ff"/></linearGradient>')
    plum, wide = "#4b2a55", w > 600
    out = [rect(0, 0, w, h, "url(#bday-bg)")]
    out.append(s.text(16 if not wide else 24, 32 if not wide else 42, "Happy birthday, [name]!", 24 if not wide else 30, plum))
    out.append(s.text(16 if not wide else 24, 52 if not wide else 66, "3D cake · honey pots · quiz · music", 15 if not wide else 18,
                      plum, attrs=' opacity=".72"'))
    cx, base = (.2 if not wide else .16) * w, h - 14
    out.append(f'<ellipse cx="{f(cx)}" cy="{f(base)}" rx="60" ry="7" fill="#fff" opacity=".85"/>')
    out.append(rect(cx - 50, base - 38, 100, 36, "#f472b6", ' rx="6"') + rect(cx - 36, base - 64, 72, 28, "#f9a8d4", ' rx="6"'))
    out.append("".join(f'<circle cx="{f(cx - 44 + k * 11)}" cy="{f(base - 37)}" r="5" fill="#fff0f7"/>' for k in range(9)))
    s.art_toggle("bday-lit", [(0, 3.4)])
    s.art_toggle("bday-smoke", [(3.4, 4.9)])
    s.art_toggle("bday-wish", [(3.7, ART)])
    s.css.append("@keyframes bday-fl{to{transform:scaleY(.72)}}"
                 ".bday-fl{transform-box:fill-box;transform-origin:50% 100%;animation:bday-fl .28s steps(2) infinite alternate}")
    flames, smoke = [], []
    for k in (-20, 0, 20):
        x = cx + k
        out.append(rect(x - 3, base - 84, 6, 20, "#a78bfa") + rect(x - 3, base - 78, 6, 3, "#fff") + rect(x - 3, base - 70, 6, 3, "#fff"))
        flames.append(f'<g class="bday-fl"><ellipse cx="{f(x)}" cy="{f(base - 92)}" rx="4.5" ry="8" fill="#ffb020"/>'
                      f'<ellipse cx="{f(x)}" cy="{f(base - 90)}" rx="2" ry="4" fill="#fff3b0"/></g>')
        smoke.append(f'<circle cx="{f(x + 2)}" cy="{f(base - 94)}" r="3.5" fill="#9b8aa8" opacity=".55"/>'
                     f'<circle cx="{f(x - 2)}" cy="{f(base - 104)}" r="4.5" fill="#9b8aa8" opacity=".35"/>')
    out.append(f'<g class="bday-lit">{"".join(flames)}</g><g class="bday-smoke" opacity="0">{"".join(smoke)}</g>')
    out.append(f'<g class="bday-wish" opacity="0">{s.text(cx, base - 118, "make a wish!", 18, plum, "middle")}</g>')
    hx = (.45 if not wide else .36) * w
    out.append(s.emoji(hx, h - 42, "🍯", 40))
    out.append(f'{rect(hx - 44, h - 104, 88, 28, "#fff", " rx=\"8\"")}'
               f'<path d="M{f(hx - 6)} {f(h - 77)}l6 8l6-8z" fill="#fff"/>{s.text(hx, h - 84, "open me!", 17, plum, "middle")}')
    if wide:
        cells = [(.5 * w + i * 114, 82, 100, 100) for i in range(4)]
    else:
        cells = [(w - 12 - 148 + (i % 2) * 78, 14 + (i // 2) * 78, 70, 70) for i in range(4)]
    for x, y, cw, ch in cells:
        out.append(rect(x, y, cw, ch, "#fff", f' opacity=".45" stroke="{plum}" stroke-opacity=".5" stroke-dasharray="4 3"')
                   + s.text(x + cw / 2, y + ch / 2 + 5, "photo", 16, plum, "middle", attrs=' opacity=".7"'))
    return "".join(out)


# ───────────────────────────── activity ─────────────────────────────


def activity():
    """My contribution calendar for YEAR, from the GitHub API (cached in data/activity.json)."""
    today = datetime.now(timezone.utc).date()
    try:
        token = os.environ.get("GITHUB_TOKEN") or subprocess.run(["gh", "auth", "token"], capture_output=True,
                                                                  text=True, check=True).stdout.strip()
        q = ("query($u:String!,$f:DateTime!,$t:DateTime!){user(login:$u){contributionsCollection(from:$f,to:$t)"
             "{contributionCalendar{weeks{contributionDays{date contributionCount}}}}}}")
        body = json.dumps({"query": q, "variables": {"u": USER, "f": f"{YEAR}-01-01T00:00:00Z",
                                                     "t": f"{min(today, date(YEAR, 12, 31))}T23:59:59Z"}}).encode()
        req = urllib.request.Request("https://api.github.com/graphql", body, {"Authorization": f"bearer {token}"})
        weeks = json.load(urllib.request.urlopen(req, timeout=20))["data"]["user"]["contributionsCollection"][
            "contributionCalendar"]["weeks"]
        days = {d["date"]: d["contributionCount"] for wk in weeks for d in wk["contributionDays"]}
        DATA.parent.mkdir(exist_ok=True)
        DATA.write_text(json.dumps({"fetched": today.isoformat(), "days": days}, indent=0) + "\n")
    except Exception as e:  # offline: use the last saved copy
        print(f"  using saved activity ({e.__class__.__name__})")
        days = json.loads(DATA.read_text())["days"]
    days = {date.fromisoformat(k): v for k, v in days.items() if k.startswith(str(YEAR))}
    first = date(YEAR, 1, 1)
    sunday = first - timedelta(days=(first.weekday() + 1) % 7)
    weeks = [0] * (((max(days) - sunday).days // 7) + 1)
    for d, c in days.items():
        weeks[(d - sunday).days // 7] += c
    return dict(weeks=weeks, total=sum(days.values()), active=sum(1 for c in days.values() if c),
                busiest=max(days.values()))


# ───────────────────────────── the CV window ─────────────────────────────


def hit(x, y, w, h, attrs):
    """An invisible click target for the live page."""
    return rect(x, y, w, h, "#000", f' fill-opacity="0" tabindex="0" {attrs}')


def arrow(x, y, color=LILAC):
    return (f'<path d="M{f(x - 5)} {f(y + 5)}l10-10m-7 0h7v7" stroke="{color}" stroke-width="2.4" fill="none" '
            f'stroke-linecap="square"/>')


def cv_window(s, x, y, w, h):
    out = [window(s, x, y, w, h, "📄", "Sewar_AlRihani_CV")[0], sunken(x + 8, y + 36, w - 16, h - 44)]
    x0, width, cy = x + 22, w - 44, y + 78
    out.append(s.text(x0, cy, CV["name"], 34, LILAC) + s.text(x0, cy + 28, CV["title"], 21))
    cy += 50
    # three highlights
    bw = (width - 16) / 3
    labels = [wrap(lab, bw - 14, 15) for _, lab in CV["kpis"]]
    bh = 40 + max(map(len, labels)) * 16
    for i, (v, _) in enumerate(CV["kpis"]):
        bx = x0 + i * (bw + 8)
        out.append(groove(bx, cy, bw, bh, "#181128") + s.text(bx + 8, cy + 28, v, 26, MINT))
        out += [s.text(bx + 8, cy + 48 + k * 16, ln, 15) for k, ln in enumerate(labels[i])]
    cy += bh + 30
    # now, before, studied
    for label, what, where in CV["rows"]:
        out.append(s.text(x0, cy, label, 15, SOFT) + s.text(x0, cy + 22, what, 20, WHITE) + s.text(x0, cy + 42, where, 17, SOFT))
        cy += 70
    cy += 8
    s.css.append("@keyframes caret{50%{opacity:0}}.caret{animation:caret .8s steps(1) infinite}")
    out.append(s.text(x0, cy, CV["cta"], 20, LILAC) + rect(x0 + len(CV["cta"]) * 8 + 4, cy - 15, 8, 17, LILAC, ' class="caret"'))
    if cy > y + h - 20:
        raise SystemExit(f"The CV window overflows by {cy - (y + h - 20):.0f}px.")
    return "".join(out)


# ───────────────────────────── the whole PC ─────────────────────────────


def hero(act, live=False):
    """The PC. In the README one project window cycles through the projects; `live` makes them clickable instead."""
    s = SVG(1000, 700, "SewarOS 98: an old purple PC. My CV window shows my current role, past role, degree and "
                       "stack, and a project window shows CareTail Echo, OCDAgent, Chefmates and Birthday Chronicle.")
    SW, SHH = 948, 600
    s.defs.append(
        '<linearGradient id="case" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#241c30"/><stop offset="1" stop-color="#17121f"/></linearGradient>'
        '<linearGradient id="tb" x1="0" y1="0" x2="1" y2="0"><stop offset="0" stop-color="#4c22b8"/><stop offset="1" stop-color="#b58cff"/></linearGradient>'
        '<linearGradient id="bar" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#e2cfff"/><stop offset="1" stop-color="#8e5ad8"/></linearGradient>'
        f'<clipPath id="scr"><rect width="{SW}" height="{SHH}" rx="10"/></clipPath>'
        '<pattern id="dots" width="4" height="4" patternUnits="userSpaceOnUse"><circle cx="2" cy="2" r=".6" fill="#fff" opacity=".05"/></pattern>'
        '<pattern id="scan" width="4" height="3" patternUnits="userSpaceOnUse"><rect width="4" height="1" fill="#fff" opacity=".03"/></pattern>'
        '<radialGradient id="vig" r=".75"><stop offset=".6" stop-color="#000" stop-opacity="0"/><stop offset="1" stop-color="#000" stop-opacity=".35"/></radialGradient>'
        + "".join(f'<radialGradient id="{i}" cx="{cx}" cy="{cy}" r="{r}"><stop offset="0" stop-color="{c}" stop-opacity="{o}"/>'
                  f'<stop offset="1" stop-color="{c}" stop-opacity="0"/></radialGradient>'
                  for i, cx, cy, r, c, o in [("w1", .12, .18, .62, "#965fff", .62), ("w2", .88, .24, .6, "#2ecc92", .30),
                                             ("w3", .58, 1.12, .8, "#5476ff", .5), ("w4", .40, .45, .45, "#e66ec8", .18)]))
    b = ['<rect width="1000" height="700" rx="22" fill="url(#case)"/>', rect(22, 20, SW + 8, SHH + 8, "#2c2a33", ' rx="13"'),
         '<g transform="translate(26,24)" clip-path="url(#scr)">', rect(0, 0, SW, SHH, "#120d1e")]
    b += [rect(0, 0, SW, SHH, f"url(#{i})") for i in ("w1", "w2", "w3", "w4", "dots")]
    T = ART * len(PROJECTS)  # each project is on screen for one loop of its picture

    def shown(cls, k, body):
        """Project k's version of something: clickable on the live page, on a timer in the README."""
        if live:
            return f'<g class="{cls}" data-k="{k}"{"" if k == 0 else " style=\"display:none\""}>{body}</g>'
        s.toggle(f"{cls}{k}", T, [(k * ART, (k + 1) * ART)])
        return f'<g class="{cls}{k}"{"" if k == 0 else " opacity=\"0\""}>{body}</g>'

    # desktop icons: the projects only
    for k, p in enumerate(PROJECTS):
        y0, lines = 22 + k * 134, wrap(p["name"], 110, 18)
        lw = max(map(len, lines)) * 7.2 + 12
        b.append(shown("sel", k, rect(62 - lw / 2, y0 + 57, lw, len(lines) * 19 + 6, SEL, ' stroke="#fff" stroke-dasharray="1 2"')))
        icon = [s.emoji(62, y0 + 26, p["emoji"], 44)]
        for i, ln in enumerate(lines):
            icon.append(s.text(63.5, y0 + 76.5 + i * 19, ln, 18, "#000", "middle", attrs=' opacity=".5"')
                        + s.text(62, y0 + 75 + i * 19, ln, 18, WHITE, "middle"))
        if live:
            b.append(f'<g class="ic" data-k="{k}" tabindex="0" role="button" aria-label="Open {escape(p["name"])}">'
                     f'{rect(6, y0 - 4, 112, 66 + len(lines) * 19, "#000", " fill-opacity=\"0\"")}{"".join(icon)}</g>')
        else:
            b += icon

    # one project window
    VX, VY, VW, VH = 130, 16, 440, 536
    for k, p in enumerate(PROJECTS):
        v = [window(s, VX, VY, VW, VH, p["emoji"], p["name"], ctl="_□×")[0]]
        ax, ay, aw, ah = VX + 13, VY + 43, VW - 26, 226 if live else 266  # the live page needs room for its button
        v.append(sunken(ax - 3, ay - 3, aw + 6, ah + 6, "#000") + art(s, ax, ay, aw, ah, p["key"]))
        tx, iy = VX + 18, ay + ah + 20
        v.append(s.emoji(tx + 18, iy + 22, p["emoji"], 38) + s.text(tx + 48, iy + 34, p["name"], 36, WHITE))
        v.append(s.text(tx, iy + 68, p["kind"], 20, SOFT))
        for i, ln in enumerate(wrap(p["short"], VW - 36, 22)):
            v.append(s.text(tx, iy + 106 + i * 26, ln, 22))
        v.append(s.text(tx, iy + 174, "  ".join("• " + c for c in p["chips"]), 20, LILAC))
        if live:
            bw_, bx, by = 150, VX + VW - 168, VY + VH - 44
            if p.get("repo"):
                v.append(f'<a href="{p["repo"]}" target="_blank" rel="noopener" aria-label="Open the {p["name"]} repo on GitHub">'
                         f'{raised(bx, by, bw_, 32, SEL)}{s.text(bx + 16, by + 22, "Open repo", 20, WHITE)}'
                         f'{arrow(bx + bw_ - 22, by + 16, WHITE)}</a>')
            else:
                v.append(groove(bx, by, bw_, 32, "#1d1533") + s.text(bx + bw_ / 2, by + 21, "Coming soon", 18, SOFT, "middle"))
        b.append(shown("pv", k, "".join(v)))

    b.append(cv_window(s, 582, 16, 356, 536))

    # taskbar: the CV, the open project, and this year's contributions
    b.append(raised(0, 566, SW, 34) + raised(6, 570, 214, 26) + s.emoji(21, 583, "📄", 15)
             + s.text(34, 589, "Sewar_AlRihani_CV", 18))
    for k, p in enumerate(PROJECTS):
        b.append(shown("job", k, f'{sunken(226, 570, 214, 26, "#342852")}{s.emoji(241, 583, p["emoji"], 15)}'
                                 f'{s.text(255, 589, p["name"], 18, WHITE)}'))
    tray = f"{YEAR}: {act['total']} contributions"
    tw = len(tray) * 7.2 + 20
    b.append(groove(SW - 6 - tw, 570, tw, 26) + s.text(SW - 6 - tw / 2, 589, tray, 18, INK, "middle"))

    # scanlines and vignette sit on top; clicks pass through them
    b += [rect(0, 0, SW, SHH, "url(#scan)", ' pointer-events="none"'), rect(0, 0, SW, SHH, "url(#vig)", ' pointer-events="none"'), "</g>"]
    # the monitor's chin
    b.append('<circle cx="46" cy="662" r="10" fill="#b58cff" opacity=".25"/><circle cx="46" cy="662" r="5" fill="#b58cff"/>'
             + s.text(62, 668, "SewarOS 98", 20, "#8a7fa6")
             + "".join(rect(880 + i * 30, 658, 22, 9, "#2f2640", ' rx="3"') for i in range(3)))
    return s.render("\n".join(b))


def project_card(p):
    """A big window for one project, shown when its section is opened in the README."""
    W, H = 1000, 400
    s = SVG(W, H, f"{p['name']}: {p['kind']}")
    s.defs.append('<linearGradient id="tb" x1="0" y1="0" x2="1" y2="0"><stop offset="0" stop-color="#4c22b8"/>'
                  '<stop offset="1" stop-color="#b58cff"/></linearGradient>')
    b = [window(s, 0, 0, W, H, p["emoji"], p["name"])[0]]
    b.append(sunken(6, 36, W - 12, H - 68, "#000") + art(s, 10, 40, W - 20, H - 76, p["key"]))
    b.append(status_bar(s, 6, H - 27, W - 12, p["status"]))
    return s.render("\n".join(b))


def button(label, face=FACE, h=44):
    w = round(len(label) * 10.4 + 70)
    s = SVG(w, h, label)
    return s.render(raised(0, 0, w, h, face) + s.text(18, h / 2 + 8, label, 26, WHITE) + arrow(w - 29, h / 2 + 1))


# ───────────────────────────── the card at the top ─────────────────────────────

CARD = dict(
    name="Sewar AlRihani",
    title="AI Engineer · Amman, Jordan",
    pitch="I design and ship production-ready RAG and multi-agent systems, in Arabic and English.",
    tags=[("Open to AI engineering roles", MINT, "#0f2a22"), ("9XAI Fellow · HTU", LILAC, "#241840")],
    build=[("🤖", "Agents", "Multi-agent systems that plan and act"),
           ("📚", "RAG", "Answers grounded in real documents"),
           ("🔊", "Audio ML", "Models that hear pets' emotions"),
           ("🌐", "Bilingual", "Arabic and English, both first-class")],
    stack=["Python", "FastAPI", "LangGraph", "LangChain", "PyTorch", "React", "Docker", "Ollama", "Hugging Face"],
)


def card(act):
    """A calm, easy-to-scan summary that sits above the PC."""
    W, H, P = 1000, 600, 40
    s = SVG(W, H, f"{CARD['name']}. {CARD['title']}. {CARD['pitch']} Open to AI engineering roles. 9XAI Fellow at "
                  f"Al Hussein Technical University. What I build: agents, RAG, audio ML, bilingual Arabic and English AI. "
                  f"Stack: {', '.join(CARD['stack'])}. {YEAR} on GitHub: {act['total']} contributions over "
                  f"{act['active']} active days.")
    s.defs.append('<linearGradient id="cardbg" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#1c1233"/>'
                  '<stop offset="1" stop-color="#110b1f"/></linearGradient>'
                  '<radialGradient id="cardglow" cx=".1" cy="0" r=".7"><stop offset="0" stop-color="#965fff" stop-opacity=".35"/>'
                  '<stop offset="1" stop-color="#965fff" stop-opacity="0"/></radialGradient>'
                  '<pattern id="cdots" width="6" height="6" patternUnits="userSpaceOnUse"><circle cx="3" cy="3" r=".7" fill="#fff" opacity=".05"/></pattern>'
                  '<linearGradient id="bar" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#e2cfff"/><stop offset="1" stop-color="#8e5ad8"/></linearGradient>')
    line = f' stroke="{LILAC}" stroke-opacity=".28"'
    b = [f'<rect width="{W}" height="{H}" rx="20" fill="url(#cardbg)"/>', f'<rect width="{W}" height="{H}" rx="20" fill="url(#cardglow)"/>',
         f'<rect width="{W}" height="{H}" rx="20" fill="url(#cdots)"/>',
         f'<rect x=".75" y=".75" width="{W - 1.5}" height="{H - 1.5}" rx="19.5" fill="none"{line} stroke-width="1.5"/>']

    # who I am
    b.append(s.text(P, 84, CARD["name"], 64, WHITE) + s.text(P, 122, CARD["title"], 28, LILAC)
             + s.text(P, 160, CARD["pitch"], 22, INK))
    s.css.append("@keyframes pulse{50%{opacity:.25}}.pulse{animation:pulse 1.6s ease-in-out infinite}")
    for i, (tag, ink, fill) in enumerate(CARD["tags"]):
        tw = len(tag) * 8 + (48 if i == 0 else 30)
        x, y = W - P - tw, 44 + i * 44
        b.append(rect(x, y, tw, 34, fill, f' rx="17" stroke="{ink}" stroke-opacity=".5"'))
        if i == 0:
            b.append(f'<circle class="pulse" cx="{x + 20}" cy="{y + 17}" r="5" fill="{ink}"/>')
        b.append(s.text(x + (34 if i == 0 else 15), y + 23, tag, 20, ink))
    b.append(rect(P, 188, W - 2 * P, 1.5, LILAC, ' opacity=".2"'))

    # what I build
    b.append(s.text(P, 226, "WHAT I BUILD", 18, SOFT, attrs=' letter-spacing="2"'))
    tw = (W - 2 * P - 3 * 16) / 4
    for i, (e, name, desc) in enumerate(CARD["build"]):
        x, y = P + i * (tw + 16), 240
        b.append(rect(x, y, tw, 118, "#221638", f' rx="12"{line}') + s.emoji(x + 30, y + 34, e, 28)
                 + s.text(x + 54, y + 43, name, 26, WHITE))
        b += [s.text(x + 18, y + 78 + k * 22, ln, 19, SOFT) for k, ln in enumerate(wrap(desc, tw - 30, 19))]

    # stack
    b.append(s.text(P, 400, "STACK", 18, SOFT, attrs=' letter-spacing="2"'))
    x = P
    for chip in CARD["stack"]:
        cw = len(chip) * 8 + 28
        b.append(rect(x, 414, cw, 36, "#241840", f' rx="8"{line}') + s.text(x + cw / 2, 438, chip, 20, INK, "middle"))
        x += cw + 10
    if x - 10 > W - P:
        raise SystemExit(f"The stack row is {x - 10 - (W - P):.0f}px too wide.")

    # this year
    b.append(s.text(P, 490, f"{YEAR} ON GITHUB", 18, SOFT, attrs=' letter-spacing="2"'))
    for i, (num, label) in enumerate([(act["total"], "contributions"), (act["active"], "active days"),
                                      (act["busiest"], "on my busiest day")]):
        x = P + i * 158
        b.append(s.text(x, 542, str(num), 46, MINT) + s.text(x, 568, label, 18, SOFT))
    cx0, cw_, top, bot = 520, W - P - 520, 500, 566
    n, peak = len(act["weeks"]), max(act["weeks"]) or 1
    bw = cw_ / n
    b += [rect(cx0 + i * bw, bot - max(2, c / peak * (bot - top)), max(1, bw - 2), max(2, c / peak * (bot - top)), "url(#bar)", ' rx="1"')
          for i, c in enumerate(act["weeks"])]
    b.append(rect(cx0, bot + 1, cw_, 1, LILAC, ' opacity=".3"') + s.text(cx0, bot + 22, "Jan", 15, SOFT)
             + s.text(cx0 + cw_, bot + 22, "this week", 15, SOFT, "end"))
    return s.render("\n".join(b))


PAGE = """<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>SewarOS 98 · Sewar AlRihani</title>
<meta name="description" content="Sewar AlRihani, AI Engineer in Amman, Jordan. Click a project on the old purple PC to open it.">
<link rel="icon" href="data:image/svg+xml,<svg xmlns=%22http://www.w3.org/2000/svg%22 viewBox=%220 0 100 100%22><text y=%22.9em%22 font-size=%2290%22>💜</text></svg>">
<style>
  :root { color-scheme: dark; }
  body { margin: 0; min-height: 100vh; color: #efe8ff; font: 15px/1.5 ui-monospace, "SF Mono", Menlo, Consolas, monospace;
         background: radial-gradient(70% 50% at 50% 0%, #2a1650, transparent 70%) #0b0714; }
  main { max-width: 1100px; margin: 0 auto; padding: 24px 16px 32px; }
  .pc { overflow-x: auto; }
  .pc svg { display: block; width: 100%; height: auto; min-width: 720px; }
  .ic, .pc svg a { cursor: pointer; }
  .ic:hover .e { filter: brightness(1.2) drop-shadow(0 0 6px #b58cff); }
  .ic:focus-visible, .pc svg a:focus-visible { outline: 2px dotted #fff; }
  .pc svg a:hover rect:last-of-type { fill: #9166ff; }
  footer { display: flex; gap: 20px; justify-content: center; flex-wrap: wrap; margin-top: 16px; }
  footer a { color: #c9a8ff; }
  .tip { display: none; text-align: center; color: #b8aadb; font-size: 13px; margin: 0 0 10px; }
  @media (max-width: 720px) { .tip { display: block; } }
</style>
</head>
<body>
<main>
<p class="tip">Tip: slide sideways to see the whole screen.</p>
<div class="pc">
__SVG__
</div>
<footer>
  <a href="https://github.com/SewarRihani">GitHub</a>
  <a href="https://www.linkedin.com/in/sewar-alrihani-613549250/">LinkedIn</a>
  <a href="mailto:sewaralrihani2@gmail.com">Email</a>
</footer>
</main>
<script>
const svg = document.querySelector(".pc svg");
const KEYS = __KEYS__;
const all = sel => [...svg.querySelectorAll(sel)];

function openProject(k) {
  ["pv", "sel", "job"].forEach(c => all("." + c).forEach(el => { el.style.display = el.dataset.k === String(k) ? "" : "none"; }));
  // play the picture from the start every time its window opens
  const pv = all(".pv").find(el => el.dataset.k === String(k));
  try { pv.getAnimations({ subtree: true }).forEach(a => { a.currentTime = 0; }); } catch (e) {}
  history.replaceState(null, "", "#" + KEYS[k]);
}

all(".ic").forEach(el => {
  el.addEventListener("click", () => openProject(+el.dataset.k));
  el.addEventListener("keydown", e => { if (e.key === "Enter" || e.key === " ") { e.preventDefault(); openProject(+el.dataset.k); } });
});
const start = KEYS.indexOf(location.hash.slice(1));
if (start >= 0) openProject(start);
</script>
</body>
</html>
"""


def main():
    ASSETS.mkdir(exist_ok=True)
    act = activity()
    print(f"  {YEAR}: {act['total']} contributions, {act['active']} active days, busiest day {act['busiest']}")
    files = {"assets/card.svg": card(act), "assets/sewaros-98.svg": hero(act), "assets/btn-linkedin.svg": button("LinkedIn"),
             "assets/btn-email.svg": button("Email"), "assets/btn-repo.svg": button("Open repo", SEL)}
    for p in PROJECTS:
        files[f"assets/project-{p['key']}.svg"] = project_card(p)
    files["docs/index.html"] = PAGE.replace("__SVG__", hero(act, live=True)).replace(
        "__KEYS__", json.dumps([p["key"] for p in PROJECTS]))
    for name, text in files.items():
        (ROOT / name).parent.mkdir(exist_ok=True)
        (ROOT / name).write_text(text)
        print(f"  {name}  {len(text.encode()) / 1024:.0f} KB")


if __name__ == "__main__":
    main()
