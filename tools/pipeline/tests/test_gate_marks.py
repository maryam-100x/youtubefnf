"""gate.py B12 MARK_MOVES: marks sit on a frozen picture. The proof on a real probe (tests/data): a mural shot's four boxes ("Arc", "Kit",
"Owl", "Lantern") over the clip while it plays fails (marks_frozen_playing); the fixed shot (the clip frozen on the first box's frame,
the design's Hold) passes (marks_frozen_held)."""
import gzip
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import gate  # noqa: E402

DATA = Path(__file__).resolve().parent / "data"


def probe(tmp_path, name):
    p = tmp_path / name.replace(".gz", "")
    p.write_text(gzip.open(DATA / name, "rt", encoding="utf-8").read(), encoding="utf-8")
    return gate.load_probe(p)


def test_marks_over_a_playing_clip_fail(tmp_path):
    clips, layout = probe(tmp_path, "marks_frozen_playing.jsonl.gz")
    flags = gate.check_marks(layout, clips)
    assert len(flags) == 1
    fl = flags[0]
    assert fl["check"] == "MARK_MOVES" and fl["key"] == "m16c_mural.mp4" and "plays" in fl["what"]
    assert fl["at"] <= 12665 and fl["to"] >= 12861   # 3:31.08 (the first box) to the cut


def test_marks_over_the_held_clip_pass(tmp_path):
    clips, layout = probe(tmp_path, "marks_frozen_held.jsonl.gz")
    assert gate.check_marks(layout, clips) == []
    # the four boxes and their names are still there, as marks on the mural
    W, H = gate.FRAME
    names = {str(layout[12860][i]["t"]) for i in gate.mark_items(layout[12860], W, H)}
    assert {"Arc", "Kit", "Owl", "Lantern"} <= names


def test_a_push_under_a_mark_fails():
    """a still page pushing 1.00 -> 1.04 under a box (a store page pushing in) is a moving ground too"""
    def frame(f, k):
        w = 1500 * k
        return [{"k": "img", "t": "page.png", "x": 960 - w / 2, "y": 300, "w": w, "h": 400 * k, "cx0": 0, "cy0": 0, "cx1": 1920, "cy1": 1080,
                 "op": 1, "br": 1, "fs": 0, "e": 0, "c": 0, "pa": -1, "g": ""},
                {"k": "box", "t": "", "x": 1400, "y": 600, "w": 230, "h": 80, "cx0": 0, "cy0": 0, "cx1": 1920, "cy1": 1080, "op": 1, "br": 1,
                 "fs": 0, "e": 1, "c": 0, "pa": -1, "g": ""}]
    moving = {f: frame(f, 1.0 + 0.04 * f / 120) for f in range(120)}
    still = {f: frame(f, 1.02) for f in range(120)}
    assert [x["check"] for x in gate.check_marks(moving, {})] == ["MARK_MOVES"]
    assert gate.check_marks(still, {}) == []


def test_a_highlight_riding_its_pushing_page_passes():
    """marks fixed on their picture, moving together with it, are fine: a highlight that rides its page through a 1.00 -> 1.04 push
    stays on its target"""
    def frame(k):
        w, h = 1500 * k, 400 * k
        x, y = 960 - w / 2, 540 - h / 2
        return [{"k": "img", "t": "page.png", "x": x, "y": y, "w": w, "h": h, "cx0": 0, "cy0": 0, "cx1": 1920, "cy1": 1080,
                 "op": 1, "br": 1, "fs": 0, "e": 0, "c": 0, "pa": -1, "g": ""},
                {"k": "box", "t": "", "x": x + 0.6 * w, "y": y + 0.5 * h, "w": 0.15 * w, "h": 0.2 * h, "cx0": 0, "cy0": 0, "cx1": 1920,
                 "cy1": 1080, "op": 1, "br": 1, "fs": 0, "e": 0, "c": 0, "pa": -1, "g": "mark"}]
    riding = {f: frame(1.0 + 0.04 * f / 120) for f in range(120)}
    assert gate.check_marks(riding, {}) == []


def test_a_mark_sliding_on_a_still_page_fails():
    """the other way round: the page stands still and the mark slides off its words"""
    def frame(f):
        return [{"k": "img", "t": "page.png", "x": 210, "y": 340, "w": 1500, "h": 400, "cx0": 0, "cy0": 0, "cx1": 1920, "cy1": 1080,
                 "op": 1, "br": 1, "fs": 0, "e": 0, "c": 0, "pa": -1, "g": ""},
                {"k": "box", "t": "", "x": 900 + 0.2 * f, "y": 500, "w": 230, "h": 80, "cx0": 0, "cy0": 0, "cx1": 1920, "cy1": 1080,
                 "op": 1, "br": 1, "fs": 0, "e": 0, "c": 0, "pa": -1, "g": "mark"}]
    flags = gate.check_marks({f: frame(f) for f in range(60)}, {})
    assert [x["check"] for x in flags] == ["MARK_MOVES"] and "slides" in flags[0]["what"]
