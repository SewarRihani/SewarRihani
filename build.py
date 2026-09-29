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

ADV = 0.4  # VT323 is monospaced: every glyph is 0.4 em wide
B = 1.5    # bevel line width

INK, SOFT, LILAC, MINT, WHITE = "#efe8ff", "#b8aadb", "#c9a8ff", "#7ef0c0", "#ffffff"
FACE, HI, HI2, SH, SH2, WELL, SEL = "#2a2042", "#7a62b8", "#4a3a78", "#07040d", "#171026", "#120c1f", "#7c4dff"
EMOJI_FONTS = '"Apple Color Emoji","Segoe UI Emoji","Noto Color Emoji",sans-serif'

# ───────────────────────────── content ─────────────────────────────

PROJECTS = [
    dict(key="care", emoji="🐾", name="CareTail Echo", kind="Vet labelling tool · graduation project",
         line="Veterinarians listen to 1,201 cat and dog recordings and label each one Positive, "
              "Negative or Unknown. Progress saves to a CSV, so a vet can stop and pick up later.",
         chips=["Streamlit", "pandas", "1,201 clips", "CSV save + resume"],
         toast="Clip 318 labelled Positive. Progress saved.",
         status=["1,201 clips", "3 labels", "saves to CSV"]),
    dict(key="ocd", emoji="🧹", name="OCDAgent", kind="Mac organiser · Python",
         line="Sorts a messy Mac into colour-coded folders with an emoji on each one. It proves "
              "duplicates byte by byte before they go, never deletes on its own, and every move can be undone.",
         chips=["Python", "launchd", "Finder tags", "no dependencies"],
         toast="Moved 93 items. 0 deleted.",
         status=["93 moved", "0 deleted", "every move undoable"]),
    dict(key="chef", emoji="🍳", name="Chefmates", kind="Two-player co-op pixel game",
         line="Salt and Pepper shrink down and search a giant kitchen for the four parts of a runaway "
              "mixer: its goal, knowledge, tool and rules. Fix it, and you've learned what an AI agent needs.",
         chips=["TypeScript", "React", "own canvas engine", "Node"],
         toast="Found the plug: knowledge. 1 of 4.",
         status=["2 players", "4 parts", "runs offline"]),
    dict(key="bday", emoji="🎂", name="Birthday Chronicle", kind="Interactive birthday website",
         line="A 3D cake whose candles you blow out, honey pots that open to kind messages, a photo "
              "gallery, a timeline with a quiz, a music player, and characters who dance when clicked.",
         chips=["React", "Three.js", "Framer Motion", "Tailwind"],
         toast="Candles blown out. Make a wish!",
         status=["3D cake", "honey pots", "quiz + music"]),
]

CV = {
    "About": [
        ("title", "SEWAR ALRIHANI"),
        ("t", "AI Engineer · Generative AI, RAG & Multi-Agent Systems"),
        ("s", "Amman, Jordan · Arabic (native) · English (professional)"),
        ("gap", 8),
        ("t", "I build RAG systems, multi-agent orchestrators and conversational AI that answer "
              "from real documents, stay grounded, and work in Arabic and English."),
        ("gap", 10),
        ("kpis", [("1 of 20", "fellows picked from 1,000+ applicants"), ("2", "AI engineering roles"),
                  ("AR + EN", "bilingual AI, both first-class")]),
        ("gap", 10),
        ("t", "Focus: grounded, reliable, production-ready AI for sensitive, data-governed settings."),
        ("gap", 8),
        ("caret", "> Open to AI engineering roles."),
    ],
    "Experience": [
        ("h", "AI Engineer (Contract)"),
        ("s", "9XAI Program · Al Hussein Technical University"),
        ("s", "Mar 2026 – now"),
        ("b", ["Agents and multi-agent orchestrators with LangGraph and Vertex AI",
               "Async sub-agents for retrieval, translation and grounding",
               "Real-time Arabic/English voice assistants",
               "Modernised back ends and data services behind live dashboards",
               "Applied ML, NLP and RAG, from prototype to production"]),
        ("h", "AI / ML Engineer Intern"),
        ("s", "Acabes International · Sep – Dec 2025"),
        ("b", ["RAG chatbots and enterprise assistants (LangChain, OpenAI, Python)",
               "Prompt engineering and evaluation to cut ungrounded answers"]),
    ],
    "Education": [
        ("h", "B.Sc. Artificial Intelligence"),
        ("s", "The University of Jordan · 2022 – 2026"),
        ("h", "Graduation project · CareTail Echo"),
        ("t", "Pet sounds in, species and emotion out (CNNs on Mel-spectrograms), plus a RAG "
              "vet-care chatbot. Flutter + Python."),
        ("h", "Also built"),
        ("b", ["Cardiac image CNN (ResNet50V2), ~91% accuracy", "IoT water monitor · ESP32 + ThingSpeak",
               "Real-time smart parking · Arduino"]),
        ("h", "Certificates"),
        ("t", "MathWorks (Machine Learning, Deep Learning, Image Processing) · Accenture Digital "
              "Skills: AI · HTU Intro to Python · CCNA fundamentals · Cybersecurity Fundamentals · UI/UX Design"),
    ],
    "Skills": [
        ("stack", [("🐍", "Python"), ("⚡", "FastAPI"), ("🦜", "LangChain"), ("🕸️", "LangGraph"), ("🔥", "PyTorch"),
                   ("⚛️", "React"), ("🟦", "TypeScript"), ("🐳", "Docker"), ("🦙", "Ollama"), ("🤗", "Hugging Face")]),
        ("h", "GenAI & agents"),
        ("t", "LangGraph · LangChain · RAG · multi-agent orchestration · prompt engineering · "
              "embeddings · OpenAI API · Vertex AI"),
        ("h", "ML & deep learning"),
        ("t", "PyTorch · TensorFlow · CNNs · NLP · Librosa · model evaluation"),
        ("h", "Build"),
        ("t", "FastAPI · REST APIs · React · Tailwind · Flutter · Git · Google Cloud"),
        ("h", "Code"),
        ("t", "Python · SQL · JavaScript · C++ · C# · Java"),
    ],
}

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
        self.art_delay = 0  # shifts the project pictures' loops so they start when their window opens

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
        self.toggle(name, ART, windows, self.art_delay)

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
    tt = TTFont(FONT)
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


def explorer_bars(s, x, y, w, name):
    """Menu bar and address bar of a Project Viewer window."""
    out, mx = [], x + 10
    for m in ["File", "Edit", "View", "Favorites", "Help"]:
        out.append(s.text(mx, y + 49, m, 16) + rect(mx, y + 51, 6.4, 1.2, INK))
        mx += len(m) * 6.4 + 16
    bx = x + 8
    for lab in ["< Back", ">", "^ Up"]:
        bw = len(lab) * 6.4 + 16
        out.append(raised(bx, y + 57, bw, 24) + s.text(bx + bw / 2, y + 74, lab, 16, INK, "middle"))
        bx += bw + 4
    out.append(sunken(bx + 4, y + 57, x + w - 10 - bx - 4, 24))
    out.append(s.text(bx + 12, y + 74, f"C:\\Projects\\{name}\\", 16))
    return "".join(out)


def status_bar(s, x, y, w, cells):
    out, cw = [], w / len(cells)
    for i, c in enumerate(cells):
        out.append(groove(x + i * cw, y, cw - 3, 21) + s.text(x + i * cw + 7, y + 16, c, 15, SOFT))
    return "".join(out)


# ───────────────────────────── project pictures ─────────────────────────────


ART = 8  # each project picture loops in 8 seconds, the time one project gets in the demo
CLICK = {"care": (3.7, True), "ocd": (2.8, False), "chef": (1.9, True), "bday": (3.3, True)}  # when the demo mouse acts


def art(s, x, y, w, h, key):
    """Draws a project's picture at (x, y). Returns it and the spot the demo mouse goes to."""
    s.defs.append(f'<clipPath id="clip-{key}"><rect width="{f(w)}" height="{f(h)}"/></clipPath>')
    inner, (px, py) = {"care": art_care, "ocd": art_ocd, "chef": art_chef, "bday": art_bday}[key](s, w, h)
    return f'<g transform="translate({f(x)},{f(y)})" clip-path="url(#clip-{key})">{inner}</g>', (x + px, y + py)


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
    d = f(s.art_delay)
    s.css.append("@keyframes care-grow{0%{transform:scaleX(0)}45%,100%{transform:scaleX(1)}}"
                 f".care-grow{{transform-box:fill-box;transform-origin:0 50%;animation:care-grow {ART}s linear {d}s infinite}}"
                 f"@keyframes care-head{{0%{{transform:translateX(0)}}45%,100%{{transform:translateX({f(w - 24)}px)}}}}"
                 f".care-head{{animation:care-head {ART}s linear {d}s infinite}}")
    out.append(f'<rect class="care-grow" x="12" y="{top}" width="{f(w - 24)}" height="{f(bot - top)}" fill="#c8a8ff" opacity=".28"/>')
    out.append(f'<rect class="care-head" x="11" y="{top - 4}" width="2" height="{f(bot - top + 8)}" fill="#c8a8ff" opacity=".9"/>')
    s.art_toggle("care-press", [(3.75, ART)])
    bx, spot = 12, None
    for i, (e, lab) in enumerate([("😊", "Positive"), ("😠", "Negative"), ("❓", "Unknown")]):
        bw_ = 30 + len(lab) * 6.8 + 12
        out.append(raised(bx, h - 44, bw_, 30) + s.emoji(bx + 16, h - 29, e, 15) + s.text(bx + 29, h - 23, lab, 17))
        if i == 0:
            out.append(f'<g class="care-press">{sunken(bx, h - 44, bw_, 30, "#3fc26a")}'
                       f'{s.emoji(bx + 17, h - 28, e, 15)}{s.text(bx + 30, h - 22, lab, 17, "#06170d")}</g>')
            spot = (bx + bw_ * .6, h - 27)
        bx += bw_ + 8
    if w > 600:
        out.append(s.text(w - 12, h - 23, "progress saved to CSV", 16, green, "end"))
    return "".join(out), spot


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
    return "".join(out), (w - 12 - sw * .4, h - 20)


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
    return "".join(out), (px + 4, py + 4)


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
    return "".join(out), (cx + 6, base - 46)


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


def pane(s, items, x, y, width, max_h, name):
    out, cy = [], y

    def line(txt, size, fill, indent=0):
        nonlocal cy
        out.append(s.text(x + indent, cy + size * .8, txt, size, fill))
        cy += size * 1.12

    for n, (kind, val) in enumerate(items):
        if kind == "title":
            line(val, 26, LILAC)
        elif kind == "h":
            cy += 8 if n else 0
            line(val, 18, LILAC)
        elif kind in ("t", "s"):
            for ln in wrap(val, width, 16):
                line(ln, 16, INK if kind == "t" else SOFT)
        elif kind == "b":
            for item in val:
                for i, ln in enumerate(wrap(item, width - 13, 16)):
                    line(("• " if i == 0 else "") + ln, 16, INK, 0 if i == 0 else 12.8)
        elif kind == "gap":
            cy += val
        elif kind == "kpis":
            bw = (width - 16) / 3
            labels = [wrap(lab, bw - 12, 14) for _, lab in val]
            bh = 34 + max(map(len, labels)) * 15
            for i, (v, _) in enumerate(val):
                bx = x + i * (bw + 8)
                out.append(groove(bx, cy, bw, bh, "#181128") + s.text(bx + 7, cy + 24, v, 22, MINT))
                out += [s.text(bx + 7, cy + 42 + k * 15, ln, 14) for k, ln in enumerate(labels[i])]
            cy += bh
        elif kind == "stack":
            cw = width / 5
            for i, (e, lab) in enumerate(val):
                cx, ry = x + cw * (i % 5 + .5), cy + (i // 5) * 54
                out.append(s.emoji(cx, ry + 16, e, 24) + s.text(cx, ry + 45, lab, 13, INK, "middle"))
            cy += math.ceil(len(val) / 5) * 54 + 4
        elif kind == "caret":
            s.css.append("@keyframes caret{50%{opacity:0}}.caret{animation:caret .8s steps(1) infinite}")
            out.append(s.text(x, cy + 13, val, 16, LILAC)
                       + rect(x + len(val) * 6.4 + 3, cy + 1, 7, 14, LILAC, ' class="caret"'))
            cy += 18
    if cy - y > max_h:
        raise SystemExit(f"The {name} tab is {cy - y:.0f}px tall; it has {max_h}px.")
    return "".join(out)


def cv_window(s, x, y, w, h, act):
    out = [window(s, x, y, w, h, "📄", "Sewar_AlRihani_CV - Profile")[0]]
    tabs, tx = list(CV), x + 6
    pane_y, pane_h = y + 60, h - 178
    for k, tab in enumerate(tabs):
        tw = len(tab) * 6.8 + 18
        s.toggle(f"tab{k}", 20, [(5 * k, 5 * k + 5)])
        out.append(raised(tx, y + 36, tw, 25) + s.text(tx + tw / 2, y + 54, tab, 17, INK, "middle"))
        out.append(f'<g class="tab{k}"{"" if k == 0 else " opacity=\"0\""}>{raised(tx, y + 33, tw, 29, WELL)}'
                   f'{rect(tx + 2, y + 58, tw - 4, 6, WELL)}{s.text(tx + tw / 2, y + 53, tab, 17, LILAC, "middle")}</g>')
        tx += tw + 2
    out.append(sunken(x + 6, pane_y, w - 12, pane_h))
    for k, tab in enumerate(tabs):
        body = pane(s, CV[tab], x + 20, pane_y + 14, w - 40, pane_h - 22, tab)
        out.append(f'<g class="tab{k}"{"" if k == 0 else " opacity=\"0\""}>{body}</g>')
    # real 2026 activity, one bar per week
    ay = pane_y + pane_h + 24
    out.append(s.text(x + 16, ay, f"{YEAR} ACTIVITY", 15, SOFT))
    out.append(sunken(x + 10, ay + 6, w - 20, 50))
    n, peak = len(act["weeks"]), max(act["weeks"]) or 1
    bw = (w - 28) / n
    for i, c in enumerate(act["weeks"]):
        bh = max(1.5, c / peak * 40)
        out.append(rect(x + 14 + i * bw, ay + 52 - bh, max(1, bw - 1.2), bh, "url(#bar)"))
    out.append(s.text(x + 16, ay + 76, f"{act['total']} contributions · {act['active']} active days · "
                                        f"busiest day {act['busiest']}", 15, SOFT))
    return "".join(out)


# ───────────────────────────── the whole PC ─────────────────────────────

CURSOR = ('<path d="M0 0h1v1h1v1h1v1h1v1h1v1h1v1h1v1h1v1h1v1h1v1h1v1h-5v1h1v1h1v2h1v2h-2v-2h-1v-1h-1v-1h-1v1h-1v1h-1v1h-1z" fill="#000"/>'
          '<path d="M1 2h1v1h1v1h1v1h1v1h1v1h1v1h1v1h1v1h1v1h-4v1h1v2h1v2h-1v-2h-1v-2h-1v-1h-1v1h-1v1h-1z" fill="#fff"/>')


def hero(act):
    s = SVG(1000, 750, "SewarOS 98: an old purple PC. My CV window shows my roles, education, skills and "
                       "real 2026 GitHub activity, while project windows open one by one: CareTail Echo, "
                       "OCDAgent, Chefmates and Birthday Chronicle.")
    SW, SHH = 948, 652
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
    b = ['<rect width="1000" height="750" rx="22" fill="url(#case)"/>', rect(22, 20, SW + 8, SHH + 8, "#2c2a33", ' rx="13"'),
         '<g transform="translate(26,24)" clip-path="url(#scr)">', rect(0, 0, SW, SHH, "#120d1e")]
    b += [rect(0, 0, SW, SHH, f"url(#{i})") for i in ("w1", "w2", "w3", "w4", "dots")]

    # timeline of the demo: every project gets 8 seconds; its window is open from OPEN to CLOSE
    SEG, OPEN, CLOSE = ART, 1.3, 7.3
    T = SEG * len(PROJECTS)
    s.art_delay = -(SEG - OPEN)  # each picture starts its loop the moment its window opens
    VX, VY, VW, VH = 118, 14, 450, 586

    # desktop icons
    icons = [(p["emoji"], p["name"]) for p in PROJECTS] + [("📦", "More soon"), ("🗑️", "Recycle Bin (empty)")]
    icon_at = []
    for k, (e, name) in enumerate(icons):
        y0, lines = 14 + k * 98, wrap(name, 92, 16)
        if k < len(PROJECTS):
            s.toggle(f"sel{k}", T, [(k * SEG + OPEN - .2, k * SEG + CLOSE)])
            lw = max(map(len, lines)) * 6.4 + 10
            b.append(f'<g class="sel{k}" opacity="{1 if k == 0 else 0}">'
                     f'{rect(58 - lw / 2, y0 + 49, lw, len(lines) * 17 + 5, SEL, " stroke=\"#fff\" stroke-dasharray=\"1 2\"")}</g>')
        b.append(s.emoji(58, y0 + 24, e, 38))
        for i, ln in enumerate(lines):
            b.append(s.text(59.5, y0 + 64.5 + i * 17, ln, 16, "#000", "middle", attrs=' opacity=".5"')
                     + s.text(58, y0 + 63 + i * 17, ln, 16, WHITE, "middle"))
        icon_at.append((64, y0 + 30))

    b.append(cv_window(s, 578, 10, 360, 598, act))

    # the hint that shows while no project is open
    open_windows = [(k * SEG + OPEN, k * SEG + CLOSE) for k in range(len(PROJECTS))]
    gaps = [(0, open_windows[0][0])] + [(open_windows[k][1], open_windows[k + 1][0]) for k in range(len(PROJECTS) - 1)] \
        + [(open_windows[-1][1], T)]
    s.toggle("hint", T, gaps)
    s.css.append("@keyframes nudge{50%{transform:translateX(-8px)}}.nudge{animation:nudge 1.6s ease-in-out infinite}")
    hx = VX + VW / 2
    b.append(f'<g class="hint" opacity="0">{s.emoji(hx, 250, "👈", 48, "nudge")}'
             f'{s.text(hx, 312, "My projects open here", 24, WHITE, "middle")}'
             f'{s.text(hx, 338, "Click them below this screen", 18, SOFT, "middle")}</g>')

    # one Project Viewer and one message box per project
    close_at = ok_at = None
    spots = []
    MX, MY, MW, MH = 150, 372, 250, 112
    for k, p in enumerate(PROJECTS):
        s.toggle(f"v{k}", T, [open_windows[k]])
        win, ctl = window(s, VX, VY, VW, VH, p["emoji"], f"{p['name']} - Project Viewer")
        close_at = ctl["×"]
        v = [win, explorer_bars(s, VX, VY, VW, p["name"])]
        mx0, my0, mw, mh = VX + 6, VY + 86, VW - 12, VH - 118
        v.append(sunken(mx0, my0, mw, mh))
        ax, ay, aw, ah = mx0 + 12, my0 + 12, mw - 24, 224
        picture, spot = art(s, ax, ay, aw, ah, p["key"])
        spots.append(spot)
        v.append(sunken(ax - 3, ay - 3, aw + 6, ah + 6, "#000") + picture)
        iy = ay + ah + 18
        v.append(s.emoji(ax + 20, iy + 18, p["emoji"], 34) + s.text(ax + 48, iy + 25, p["name"], 30, WHITE)
                 + s.text(ax + 48, iy + 45, p["kind"], 16, SOFT))
        ty = iy + 78
        for ln in wrap(p["line"], aw, 17):
            v.append(s.text(ax, ty, ln, 17))
            ty += 20
        ty += 12
        v += [s.text(ax + (i % 2) * aw / 2, ty + (i // 2) * 22, "• " + c, 17, LILAC) for i, c in enumerate(p["chips"])]
        v.append(status_bar(s, VX + 6, VY + VH - 27, VW - 12,
                            [f"{len(PROJECTS)} projects", f"{act['total']} contributions", "0 files deleted"]))
        b.append(f'<g class="v{k}" opacity="{1 if k == 0 else 0}">{"".join(v)}</g>')

        s.toggle(f"m{k}", T, [(k * SEG + 5.3, k * SEG + 6.3)])  # after the picture has done its thing
        mwin, _ = window(s, MX, MY, MW, MH, p["emoji"], p["name"], ctl="×")
        m = [mwin, f'<circle cx="{MX + 30}" cy="{MY + 60}" r="16" fill="{SEL}"/>',
             s.text(MX + 30, MY + 68, "i", 26, WHITE, "middle")]
        m += [s.text(MX + 58, MY + 56 + i * 18, ln, 16) for i, ln in enumerate(wrap(p["toast"], MW - 70, 16))]
        m.append(raised(MX + MW / 2 - 35, MY + MH - 32, 70, 24)
                 + rect(MX + MW / 2 - 30, MY + MH - 28, 60, 16, "none", f' stroke="{INK}" stroke-dasharray="1 2"')
                 + s.text(MX + MW / 2, MY + MH - 15, "OK", 17, INK, "middle"))
        ok_at = (MX + MW / 2, MY + MH - 20)
        b.append(f'<g class="m{k}" opacity="0">{"".join(m)}</g>')

    # taskbar: no Start button, just the open windows and a clock
    b.append(raised(0, 618, SW, 34) + raised(6, 622, 196, 26) + s.emoji(20, 635, "📄", 14)
             + s.text(32, 640, "Sewar_AlRihani_CV", 16))
    for k, p in enumerate(PROJECTS):
        s.toggle(f"j{k}", T, [open_windows[k]])
        b.append(f'<g class="j{k}" opacity="{1 if k == 0 else 0}">{sunken(208, 622, 186, 26, "#342852")}'
                 f'{s.emoji(223, 635, p["emoji"], 14)}{s.text(236, 640, p["name"], 16, WHITE)}</g>')
    b.append(groove(SW - 118, 622, 112, 26) + s.emoji(SW - 100, 635, "🔊", 13) + s.text(SW - 86, 640, "12:15 PM", 16))

    # the mouse that shows it all off
    # double-click the icon, act in the picture, OK the message, close the window
    moves, clicks = [(0, close_at)], []
    for k, p in enumerate(PROJECTS):
        t0 = k * SEG
        at, click = CLICK[p["key"]]
        tc = t0 + OPEN + at
        moves += [(t0 + .2, close_at), (t0 + 1.0, icon_at[k]), (tc - .9, icon_at[k]), (tc - .1, spots[k]),
                  (t0 + 5.4, spots[k]), (t0 + 5.95, ok_at), (t0 + 6.4, ok_at), (t0 + 7.0, close_at)]
        clicks += [t0 + 1.05, t0 + 1.22] + ([tc - .05] if click else []) + [t0 + 6.2, t0 + 7.1]
    moves.append((T, close_at))
    assert all(a[0] < b[0] for a, b in zip(moves, moves[1:])), "the mouse's timeline must move forward"
    frames = "".join(f"{f(t / T * 100)}%{{transform:translate({f(x)}px,{f(y)}px)}}" for t, (x, y) in moves)
    press = "".join(f"{f(t / T * 100)}%{{transform:scale(.8)}}{f((t + .08) / T * 100)}%{{transform:scale(1)}}" for t in clicks)
    s.css.append(f"@keyframes cur{{{frames}}}.cur{{animation:cur {T}s steps(10,end) infinite}}"
                 f"@keyframes press{{0%{{transform:scale(1)}}{press}100%{{transform:scale(1)}}}}"
                 f".press{{transform-box:fill-box;transform-origin:0 0;animation:press {T}s steps(1,end) infinite}}")
    b.append(f'<g class="cur" transform="translate({f(close_at[0])},{f(close_at[1])})"><g class="press">'
             f'<g transform="scale(1.6)" shape-rendering="crispEdges">{CURSOR}</g></g></g>')

    b += [rect(0, 0, SW, SHH, "url(#scan)"), rect(0, 0, SW, SHH, "url(#vig)"), "</g>"]
    # the monitor's chin
    b.append('<circle cx="46" cy="712" r="10" fill="#b58cff" opacity=".25"/><circle cx="46" cy="712" r="5" fill="#b58cff"/>'
             + s.text(62, 718, "SewarOS 98", 20, "#8a7fa6")
             + "".join(rect(880 + i * 30, 708, 22, 9, "#2f2640", ' rx="3"') for i in range(3)))
    return s.render("\n".join(b))


def project_card(p, act):
    """A big Project Viewer window for one project, shown when its section is opened in the README."""
    W, H = 1000, 400
    s = SVG(W, H, f"{p['name']}: {p['kind']}")
    s.defs.append('<linearGradient id="tb" x1="0" y1="0" x2="1" y2="0"><stop offset="0" stop-color="#4c22b8"/>'
                  '<stop offset="1" stop-color="#b58cff"/></linearGradient>')
    b = [window(s, 0, 0, W, H, p["emoji"], f"{p['name']} - Project Viewer")[0], explorer_bars(s, 0, 0, W, p["name"])]
    b.append(sunken(6, 86, W - 12, H - 118, "#000") + art(s, 10, 90, W - 20, H - 126, p["key"])[0])
    b.append(status_bar(s, 6, H - 27, W - 12, p["status"]))
    return s.render("\n".join(b))


def button(label, w=190, h=44):
    s = SVG(w, h, label)
    arrow = (f'<path d="M{w - 34} {h / 2 + 6}l10-10m-7 0h7v7" stroke="{LILAC}" stroke-width="2.4" fill="none" '
             f'stroke-linecap="square"/>')
    return s.render(raised(0, 0, w, h) + s.text(18, h / 2 + 8, label, 26, WHITE) + arrow)


def main():
    ASSETS.mkdir(exist_ok=True)
    act = activity()
    print(f"  {YEAR}: {act['total']} contributions, {act['active']} active days, busiest day {act['busiest']}")
    files = {"sewaros-98.svg": hero(act), "btn-linkedin.svg": button("LinkedIn"), "btn-email.svg": button("Email")}
    for p in PROJECTS:
        files[f"project-{p['key']}.svg"] = project_card(p, act)
    for name, svg in files.items():
        (ASSETS / name).write_text(svg)
        print(f"  assets/{name}  {len(svg.encode()) / 1024:.0f} KB")


if __name__ == "__main__":
    main()
