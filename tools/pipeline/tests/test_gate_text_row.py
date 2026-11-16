"""gate.py B13 TEXT_OVERLAP and B14 ROW_CENTRE. The proof on a real probe (tests/data/text_row.jsonl.gz): two name lines under two covers
at 26:57 ("Model A the first built" running 12 px into "Model B, the one after that") and a row of three devices at 27:03 (the row
doesn't look centred left to right: "Desk Lamp Mk5" runs 64 px past its narrow picture, the row's visible content 32 px right of
centre) fail. B13's second half, a text running out of its card, and the 2 px / 8 px thresholds are proven on small synthetic frames."""
import gzip
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import gate  # noqa: E402

DATA = Path(__file__).resolve().parent / "data"


def probe(tmp_path, name):
    p = tmp_path / name.replace(".gz", "")
    p.write_text(gzip.open(DATA / name, "rt", encoding="utf-8").read(), encoding="utf-8")
    return gate.load_probe(p)[1]


def text(t, x, y, w, h, fs=52, pa=-1, g=""):
    return {"k": "text", "t": t, "x": x, "y": y, "w": w, "h": h, "cx0": -1e9, "cy0": -1e9, "cx1": 1e9, "cy1": 1e9, "op": 1, "br": 1,
            "fs": fs, "e": 0, "c": 0, "pa": pa, "g": g}


def box(x, y, w, h, pa=-1):
    return {"k": "box", "t": "", "x": x, "y": y, "w": w, "h": h, "cx0": -1e9, "cy0": -1e9, "cx1": 1e9, "cy1": 1e9, "op": 1, "br": 1,
            "fs": 0, "e": 0, "c": 1, "pa": pa, "g": ""}


def pic(name, x, y, w, h):
    return {"k": "img", "t": name, "x": x, "y": y, "w": w, "h": h, "cx0": -1e9, "cy0": -1e9, "cx1": 1e9, "cy1": 1e9, "op": 1, "br": 1,
            "fs": 0, "e": 0, "c": 0, "pa": -1, "g": ""}


def test_cover_names_overlap(tmp_path):
    layout = probe(tmp_path, "text_row.jsonl.gz")
    flags = gate.check_text_overlap(layout)
    assert [f["check"] for f in flags] == ["TEXT_OVERLAP"]
    assert "Model A the first built" in flags[0]["key"] and "Model B, the one after that" in flags[0]["key"]
    assert flags[0]["at"] <= 97020 <= flags[0]["to"]   # 26:57
    # B4's TEXT_ON_TEXT (15% of the smaller box) never sees it
    assert not [f for f in gate.check_layout(layout) if f["check"] == "TEXT_ON_TEXT"]


def test_device_row_off_centre(tmp_path):
    layout = probe(tmp_path, "text_row.jsonl.gz")
    flags = [f for f in gate.check_row_centre(layout, tmp_path) if "s99_lm5_cut" in f["key"]]
    assert len(flags) == 1 and "+32 px" in flags[0]["what"]
    assert flags[0]["at"] <= 97460 + 40 and flags[0]["to"] >= 97500   # 27:03-27:05, the row at rest


def test_overlap_threshold():
    two = lambda gap: {f: [text("left words", 100, 500, 400, 60), text("right words", 500 - gap, 500, 400, 60)] for f in range(30)}
    assert gate.check_text_overlap(two(1)) == []        # 1 px: touching, not over
    assert [f["check"] for f in gate.check_text_overlap(two(3))] == ["TEXT_OVERLAP"]


def test_text_out_of_its_card():
    """a post title running past its card's right edge"""
    def frame(over):
        return [box(300, 300, 1300, 400), text("The Harbor Market Update Has Changed The Whole Town", 360, 560, 1240 + over, 56, pa=0)]
    assert gate.check_text_overlap({f: frame(0) for f in range(30)}) == []
    flags = gate.check_text_overlap({f: frame(60) for f in range(30)})
    assert len(flags) == 1 and "out of its card" in flags[0]["key"]


def test_row_centre_threshold(tmp_path):
    def row(shift, gap2=64):
        return [pic("a.png", 400 + shift, 300, 300, 400), pic("b.png", 764 + shift, 300, 392, 400), pic("c.png", 1220 + shift + gap2 - 64, 300, 300, 400)]
    still = lambda items: {f: items for f in range(40)}
    assert gate.check_row_centre(still(row(0)), tmp_path) == []
    assert [f["check"] for f in gate.check_row_centre(still(row(12)), tmp_path)] == ["ROW_CENTRE"]
    # unequal gaps, centred: 64 and 104 px, the row shifted back by half the difference
    flags = gate.check_row_centre(still([pic("a.png", 380, 300, 300, 400), pic("b.png", 744, 300, 392, 400), pic("c.png", 1240, 300, 300, 400)]), tmp_path)
    assert len(flags) == 1 and "unequal gaps" in flags[0]["what"]
