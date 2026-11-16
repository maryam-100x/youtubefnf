"""qa_marks.py (a mark only where there is a choice, measured on its target). A synthetic page drawn with PIL (dark lines of text on
white) shown 1:1 in a card, with probe-like items as gate.load_probe returns them: a tight box passes, a box moved onto the next line and
a border through the letters are MARK_OFF, a loose box is LOOSE only (info, left as it is), a box over the only text in a small crop is
MARK_REDUNDANT."""
import sys
from pathlib import Path

import numpy as np
import pytest
from PIL import Image, ImageDraw, ImageFont

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import gate  # noqa: E402
import qa_marks  # noqa: E402

LINES = ["Northwind sold seven million tickets", "on the first day of the summer fair", "and the servers could not keep up"]
PX, PY = 60, 40          # where the text starts on the page
PITCH = 64               # px from one line to the next
CARD = (200, 300)        # where the page's top-left sits on the frame (film px; the page is shown 1:1)


def _font():
    for name in ("arial.ttf", "DejaVuSans.ttf"):
        try:
            return ImageFont.truetype(name, 40)
        except OSError:
            continue
    return ImageFont.load_default(size=40)


@pytest.fixture(scope="module")
def page(tmp_path_factory):
    """the page PNG in a public dir, and the ink box of every word on it (page px)"""
    pub = tmp_path_factory.mktemp("pub")
    (pub / "pages").mkdir()
    im = Image.new("RGB", (1300, 260), (255, 255, 255))
    dr = ImageDraw.Draw(im)
    f = _font()
    for i, ln in enumerate(LINES):
        dr.text((PX, PY + i * PITCH), ln, fill=(25, 25, 25), font=f)
    im.save(pub / "pages" / "test.png")
    ink = np.asarray(im.convert("L")) < 128
    words = {}
    # each word's ink box from the pixels, found by its drawn advance
    for i, ln in enumerate(LINES):
        pos = 0
        for w in ln.split(" "):
            k = ln.index(w, pos)
            a = PX + dr.textlength(ln[:k], font=f)
            b = PX + dr.textlength(ln[:k + len(w)], font=f)
            band = ink[PY + i * PITCH - 10:PY + i * PITCH + PITCH - 10, int(a):int(np.ceil(b))]
            ys, xs = np.nonzero(band)
            words[(i, w)] = (int(a) + xs.min(), PY + i * PITCH - 10 + ys.min(), int(a) + xs.max() + 1, PY + i * PITCH - 10 + ys.max() + 1)
            pos = k + len(w)
    return pub, words


def item(k, x, y, w, h, clip, **kw):
    it = {"k": k, "t": "", "x": x, "y": y, "w": w, "h": h, "cx0": clip[0], "cy0": clip[1], "cx1": clip[2], "cy1": clip[3], "op": 1, "br": 1,
          "fs": 0, "e": 0, "c": 0, "pa": -1, "g": ""}
    it.update(kw)
    return it


def layout(box, card=None, outline=False, frames=12):
    """one card (a filled box) holding the page 1:1 and one mark; box = the mark's rect in page px (x0, y0, x1, y1)"""
    cx, cy = CARD
    cb = card or (0, 0, 1300, 260)                       # the card's visible part of the page, page px
    clip = (cx + cb[0], cy + cb[1], cx + cb[2], cy + cb[3])
    full = (-1e9, -1e9, 1e9, 1e9)
    items = [item("box", clip[0], clip[1], clip[2] - clip[0], clip[3] - clip[1], full, c=123),
             item("img", cx, cy, 1300, 260, clip, t="pages/test.png", pa=0)]
    x0, y0, x1, y1 = box
    r, g, b = qa_marks.BRAND                           # gate.tsx's colour hash of an accent outline / an accent wash
    sig = qa_marks._sig(f"rgba({r}, {g}, {b}, 0.2)rgb({r}, {g}, {b})none") if outline else qa_marks._sig(f"rgb({r}, {g}, {b})none")
    items.append(item("box", cx + x0, cy + y0, x1 - x0, y1 - y0, clip, e=1 if outline else 0, c=sig, g="mark", pa=0,
                      op=1 if outline else 0.85))
    return {f: [dict(i) for i in items] for f in range(frames)}


def pad(b, p):
    return (b[0] - p, b[1] - p, b[2] + p, b[3] + p)


def phrase(words, line, a, b):
    """the ink box of the words a..b (inclusive) on a line"""
    ws = LINES[line].split(" ")
    bs = [words[(line, w)] for w in ws[ws.index(a):ws.index(b) + 1]]
    return (min(q[0] for q in bs), min(q[1] for q in bs), max(q[2] for q in bs), max(q[3] for q in bs))


def run(pub, lay):
    gate.FRAME[:] = [1920, 1080]
    rows = []
    flags = qa_marks.check_marks_target(pub, lay, {}, None, report=rows)
    assert len(rows) == 1
    return flags, rows[0]


def test_a_tight_box_passes(page):
    pub, words = page
    flags, row = run(pub, layout(pad(phrase(words, 0, "seven", "million"), 8)))
    assert flags == [] and row["verdict"] == "OK"


def test_a_tight_outline_passes(page):
    pub, words = page
    b = phrase(words, 0, "seven", "million")
    flags, row = run(pub, layout((b[0] - 8, b[1] - 8, b[2] + 8, b[3] + 8), outline=True))
    assert flags == [] and row["verdict"] == "OK"


def test_a_box_moved_onto_the_next_line_is_off(page):
    pub, words = page
    b = pad(phrase(words, 0, "seven", "million"), 8)
    flags, row = run(pub, layout((b[0], b[1] + PITCH // 2, b[2], b[3] + PITCH // 2)))
    assert [f["check"] for f in flags] == ["MARK_OFF"]
    assert "letters" in flags[0]["what"]


def test_a_border_through_the_letters_is_off(page):
    pub, words = page
    b = phrase(words, 0, "seven", "million")
    mid = (words[(0, "million")][0] + words[(0, "million")][2]) // 2        # the right edge halfway through "million"
    flags, row = run(pub, layout((b[0] - 8, b[1] - 8, mid, b[3] + 8), outline=True))
    assert [f["check"] for f in flags] == ["MARK_OFF"]
    assert "border runs through the letters on the right" in flags[0]["what"]


def test_a_loose_box_is_loose_only(page):
    pub, words = page
    b = phrase(words, 2, "keep", "up")                                         # the line's last words: blank page to their right
    flags, row = run(pub, layout((b[0] - 8, b[1] - 8, b[2] + 40, b[3] + 8)))
    assert flags == [] and row["verdict"] == "LOOSE"
    assert row["blank"]["right"] >= qa_marks.LOOSE_PX


def test_a_box_over_the_only_text_in_a_small_crop_is_redundant(page):
    pub, words = page
    b = words[(0, "Northwind")]
    crop = (b[0] - 30, b[1] - 20, b[2] + 30, b[3] + 20)                       # the card shows that one word
    flags, row = run(pub, layout(pad(b, 8), card=crop))
    assert [f["check"] for f in flags] == ["MARK_REDUNDANT"]


def test_the_same_box_in_the_whole_page_is_not_redundant(page):
    pub, words = page
    flags, row = run(pub, layout(pad(words[(0, "Northwind")], 8)))
    assert flags == []


def test_a_crop_png_is_written_for_a_flag(page, tmp_path):
    pub, words = page
    b = pad(phrase(words, 0, "seven", "million"), 8)
    gate.FRAME[:] = [1920, 1080]
    flags = qa_marks.check_marks_target(pub, layout((b[0], b[1] + PITCH // 2, b[2], b[3] + PITCH // 2)), {}, None, out=tmp_path)
    assert flags and Path(flags[0]["crop"]).exists()
    assert flags[0]["at"] == 0 and flags[0]["to"] == 11
