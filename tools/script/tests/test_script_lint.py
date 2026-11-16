"""The script gate's tests: lines with the mistakes the lint exists for must be flagged, and plain human lines must pass. The fixtures
are written here (invented lines), so the tests run on a fresh clone with an empty niche.json and no videos yet.

  PIPE -m pytest tools/script/tests/test_script_lint.py -q"""
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))
import script_lint as L  # noqa: E402

FLAGGED = [
    "They put out one.",
    "It finally makes it two.",
    "They sold it for one pound, plus its debts.",
    "In 2008 Acme, the company behind the best-selling phone, bought the shop.",
    "The whole deal was worth $38 billion.",
    "I think this time, the show gets a second season.",
]


def run(path, **kw):
    lines, script = L.lint(str(path), **kw)
    by_beat = {ln["beat"]: [f["rule"] for f in ln["flags"]] for ln in lines}
    return by_beat, script


def has(rules, start):
    return any(r.startswith(start) for r in rules)


def write(tmp_path, lines, name="script.txt"):
    p = tmp_path / name
    p.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return p


def test_vague_and_pointless_lines_are_flagged(tmp_path):
    by, _ = run(write(tmp_path, FLAGGED), fmt="long")
    assert has(by["L1"], "a count without its noun"), by["L1"]          # "they put out one"
    assert has(by["L2"], "a count without its noun"), by["L2"]          # "makes it two"
    assert has(by["L3"], "a money word with no figure"), by["L3"]       # "plus its debts" without the figure
    assert has(by["L4"], "a descriptor said as of today"), by["L4"]     # "the company behind" in a line set in 2008
    assert has(by["L5"], "a big number stated without its point"), by["L5"]   # "$38 billion" with no comparison
    assert has(by["L6"], "'this time'"), by["L6"]                       # "this time": say which, by its name
    assert has(by["L6"], "an opinion with no lead-in"), by["L6"]        # the take shares nothing with the lines before it


def test_plain_lines_pass(tmp_path):
    by, script = run(write(tmp_path, ["My grandmother baked bread every Sunday.", "Her kitchen smelled like warm butter and smoke."]),
                     fmt="long")
    assert by == {"L1": [], "L2": []}, by
    assert script["shape_flags"] == [], script["shape_flags"]


def test_long_script_shape_flags(tmp_path):
    lines = [f"In {1990 + k} the city council said the bridge needed more work." for k in range(20)]
    lines[5] = "Subscribe, it helps the channel."
    lines += ["The river runs past the old mill on the east side of town."] * 20
    _, script = run(write(tmp_path, lines), fmt="long")
    shape = " | ".join(why for why, _ in script["shape_flags"])
    assert "sub ask (L6)" in shape and "too early" in shape, shape        # the sub ask a few lines in
    assert "open on a date" in shape and "no line announces" in shape, shape   # the past as an unannounced timeline
    assert "reporter's share" in shape, shape                               # half the lines report what someone said


def test_copies_and_channel_lines():
    line = "The old bridge across the river closed for repairs last spring."
    hits = L.copies([("S1", line)], [("07", "S3", line)])
    assert hits["S1"][0][0].startswith("also in 07 S3 (the same sentence)"), hits
    own = "If you enjoyed this, a like helps a lot and see you in the next one."
    assert L.copies([("S9", own)], [("07", "S40", own)]) == {}       # the channel's own sign-off line is never a copy


def test_name_before_a_role_is_not_vague():
    t = "Maria Lopez is the boss of Acme, the company that owns Brightline."
    assert L.name_before(t, t.index("the company"))
    assert not L.name_before("He is the boss of the company that owns the brand.", 10)


def test_unowned_number():
    assert L.unowned_number("Analysts expect forty million units in its first four months.")
    assert not L.unowned_number("Analysts expect the Nova X to sell forty million units.")
    assert not L.unowned_number("Apollo 11 has no landing date at all.")   # a name's number is not a count
