"""The creator's look (tools/motion/src/look.json): every starting look and the default are whole looks on the font shelf, a broken
look is refused with each fault named, the gate reads the sign-off's words from the look, and the captions' font, colours and pop
come from it."""
import json
import re
import sys
from pathlib import Path

TOOLS = Path(__file__).resolve().parents[2]
MOTION = TOOLS / "motion"
sys.path.insert(0, str(MOTION))
sys.path.insert(0, str(TOOLS / "pipeline"))
sys.path.insert(0, str(TOOLS))
import look_board  # noqa: E402
import gate  # noqa: E402

LOOKS = sorted((MOTION / "looks").glob("*.json"))


def read(f):
    return json.loads(Path(f).read_text(encoding="utf-8"))


def test_starting_looks_are_whole():
    assert len(LOOKS) >= 4
    for f in LOOKS:
        assert look_board.problems(read(f)) == [], f.name


def test_default_look_is_a_starting_one_and_brand_matches_it():
    cur = read(MOTION / "src" / "look.json")
    assert look_board.problems(cur) == []
    assert any(read(f) == cur for f in LOOKS), "src/look.json is not one of tools/motion/looks/ as is"
    brand = re.search(r"^export const BRAND = '(#[0-9A-Fa-f]{6})';", (MOTION / "src" / "brand.ts").read_text(encoding="utf-8"), re.M)[1]
    assert brand.upper() == cur["colors"]["key"].upper()


def test_shelf_is_every_import():
    src = (MOTION / "src" / "fonts.ts").read_text(encoding="utf-8")
    imports = re.findall(r"^import \* as \w+ from '@remotion/google-fonts/(\w+)';", src, re.M)
    shelf = look_board.shelf()
    assert len(shelf) == len(imports)
    assert {s.replace(" ", "") for s in shelf} == set(imports)


def test_broken_look_names_each_fault():
    b = read(LOOKS[0])
    b["fonts"]["display"]["family"] = "Not A Font"
    b["colors"]["key"] = "orange"
    del b["stamp"]["tilt"]
    b["shape"]["shadow"] = "glow"
    bad = " | ".join(look_board.problems(b))
    for part in ("Not A Font", "colors.key should be a colour", "stamp.tilt is missing", "shape.shadow is one of",
                 "colors.key and captions.key"):
        assert part in bad, part


def test_gate_reads_signoff_words_from_the_look():
    so = read(MOTION / "src" / "look.json")["signoff"]
    w = gate.signoff_words()
    assert w == {k: so[k].strip().upper() for k in ("like", "liked", "comment")}


def test_captions_take_the_look(tmp_path, monkeypatch):
    from dj import core
    look = read(LOOKS[0])
    f = tmp_path / "look.json"
    f.write_text(json.dumps(look), encoding="utf-8")
    monkeypatch.setattr(core, "LOOK", f)
    cfg = core.apply_look({"brand": {"fonts": {"heavy": "Anton:wght@400"}}, "visuals": {}})
    c, cap = look["captions"], look["fonts"]["caption"]
    assert cfg["brand"]["fonts"]["heavy"] == f"{cap['family']}:wght@{cap['weight']}"
    assert cfg["brand"]["caption_key"] == c["key"] and cfg["brand"]["yellow"] == c["key"]
    assert cfg["brand"]["caption_upper"] == c["upper"]
    assert cfg["visuals"]["hero_pop_over"] == c["pop_over"]
