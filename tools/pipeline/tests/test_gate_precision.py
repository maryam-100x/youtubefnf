"""The gate's by-design cases, told apart inside its checks (so a flag means a fault), and the incremental probe's pieces (reprobe.py).
Synthetic probes; the measured numbers are in standard/PIPELINE.md."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import gate  # noqa: E402
import reprobe  # noqa: E402

W, H = 1920, 1080


def item(k, t="", x=0, y=0, w=10, h=10, op=1.0, **kw):
    d = {"k": k, "t": t, "x": x, "y": y, "w": w, "h": h, "cx0": -1e9, "cy0": -1e9, "cx1": 1e9, "cy1": 1e9, "op": op, "br": 1.0, "fs": kw.pop("fs", 0),
         "e": kw.pop("e", 0), "c": 0, "pa": kw.pop("pa", -1), "g": kw.pop("g", "")}
    d.update(kw)
    return d


def test_empty_slot_skips_marks_on_pictures():
    page = item("img", "v/pages/p.png", 200, 200, 1400, 600)
    mark = item("box", "", 400, 400, 300, 60, e=1)                   # an outline on the page: a mark
    named = item("box", "", 900, 400, 300, 60, e=1, g="mark")       # a mark that names itself
    slot = item("box", "", 300, 850, 400, 200, e=1)                  # an outline on nothing: an empty slot
    lay = {f: [page, mark, named, slot] for f in range(40)}
    gate.FRAME[:] = [W, H]
    flags = [f for f in gate.check_layout(lay) if f["check"] == "EMPTY_SLOT"]
    assert len(flags) == 1 and "300,850" in flags[0]["what"]


def test_text_overlap_ignores_rows_passing_mid_move():
    lay = {}
    for f in range(30):   # two rows gliding past each other: both move every frame
        lay[f] = [item("text", "Overview", 100, 300 + 4 * f, 400, 40, fs=36), item("text", "Part 2", 100, 420 - 4 * f, 400, 40, fs=36)]
    assert gate.check_text_overlap(lay) == []
    for f in range(30):   # the same two texts at rest, overlapping (two name lines under two covers)
        lay[f] = [item("text", "the first one built", 100, 300, 400, 40, fs=36), item("text", "the one after that", 480, 300, 400, 40, fs=36)]
    assert len(gate.check_text_overlap(lay)) == 1


def test_twice_skips_a_loop_but_not_a_second_use():
    plays = [{"src": "v/clips/loop.mp4", "f0": 0, "f1": 59, "s0": 1.0, "s1": 1.98, "n": 60},
             {"src": "v/clips/loop.mp4", "f0": 60, "f1": 119, "s0": 1.0, "s1": 1.98, "n": 60},
             {"src": "v/clips/loop.mp4", "f0": 5000, "f1": 5059, "s0": 1.0, "s1": 1.98, "n": 60}]
    lay = {f: [item("clip", "v/clips/loop.mp4", 0, 0, W, H)] for f in (30, 90, 5030)}
    flags = gate.check_twice(plays, lay, {})
    assert len(flags) == 2 and all(f["at"] == 5000 for f in flags)   # the far use against both, the restart never


def test_still_exemptions():
    gate.FRAME[:] = [W, H]
    push = {f: [item("img", "v/img/art.jpg", -f * 0.4, -f * 0.2, W * (1 + 0.0004 * f), H * (1 + 0.0004 * f))] for f in range(60)}
    assert gate.pushed(push, 30)                       # 1.00 -> 1.024 over 1 s: the house push
    still = {f: [item("img", "v/img/art.jpg", 0, 0, W, H)] for f in range(60)}
    assert not gate.pushed(still, 30)
    card = [item("text", "We have every reason to think this will continue", 200, 400, 1400, 60, fs=48)]
    assert gate.reading(card)
    assert not gate.reading([item("text", "Model B", 200, 400, 400, 60, fs=120)])


def test_mark_ground_takes_a_page_that_holds_the_mark():
    gate.FRAME[:] = [W, H]
    ground = item("clip", "v/clips/x_g.mp4", 0, 0, W, H)
    page = item("img", "v/pages/news.png", 120, 420, 1300, 260)
    mark = item("box", "", 145, 458, 1058, 147, e=1, g="mark")
    g, _ = gate.mark_ground([ground, page, mark], 2, W, H)
    assert g is page


def test_signed_off_follows_its_code(tmp_path, monkeypatch):
    f = tmp_path / "proto.tsx"
    f.write_text("a", encoding="utf-8")
    monkeypatch.setattr(gate, "REPO", tmp_path)
    sha = gate.files_sha(["proto.tsx"])   # signed on the code as the creator passed it

    class V:
        def section(self, name):
            return {"signed": [{"frames": "0-100", "files": ["proto.tsx"], "sha": sha, "note": "passed as it is"}]}
    flags = [{"check": "REVERSE", "at": 50, "key": "x", "what": ""}, {"check": "STILL", "at": 500, "key": "y", "what": ""}]
    keep, signed, stale = gate.signed_off(V(), flags)
    assert [x["at"] for x in keep] == [500] and len(signed) == 1 and not stale
    f.write_text("b", encoding="utf-8")   # the code the creator passed changed: its flags count again
    keep, signed, stale = gate.signed_off(V(), flags)
    assert len(keep) == 2 and not signed and stale


def test_reprobe_moves_lines_and_aligns_shots():
    ln = 'layout|{"frame":120,"W":1920,"H":1080,"items":[],"ats":[118]}'
    assert reprobe.line_frame(ln) == 120
    m = reprobe.moved(ln, 106)
    assert reprobe.line_frame(m) == 106 and '"ats":[104]' in m
    c = 'clip|{"abs":120,"src":"a.mp4","f":3,"s":0.05}'
    assert reprobe.line_frame(reprobe.moved(c, 100)) == 100
    assert reprobe.same_frame([ln], [m]) and not reprobe.same_frame([ln], [ln.replace("[]", '[{"k":"img"}]')])
    by = {f: [f'layout|{{"frame":{f},"items":[]}}'] for f in range(300)}
    out = reprobe.reindex(by, [(0, 99, 0), (114, 299, -14)])   # 14 frames cut at 100
    assert sorted(out) == list(range(0, 100)) + list(range(100, 286))
    assert reprobe.line_frame(out[100][0]) == 100 and '"frame":100' in out[100][0]


def test_plan_reuses_shifted_shots_and_probes_the_seam(monkeypatch, tmp_path):
    old = {"total": 600, "files": {"v/a.tsx": "1"}, "shots": [
        {"at": 0, "end": 2, "sig": "A", "names": ["Foot"]}, {"at": 2, "end": 5, "sig": "B", "names": ["Receipt"]},
        {"at": 5, "end": 10, "sig": "C", "names": ["Foot"]}]}
    new = {"total": 585, "files": {"v/a.tsx": "1"}, "imports": {}, "decl": {}, "shots": [
        {"at": 0, "end": 2, "sig": "A", "names": ["Foot"]}, {"at": 2, "end": 4.75, "sig": "B2", "names": ["Receipt"]},
        {"at": 4.75, "end": 9.75, "sig": "C", "names": ["Foot"]}]}
    p = reprobe.plan(None, old, new)
    assert p["full"] is None
    assert (0, 119, 0) in p["map"] and (300, 599, -15) in p["map"]          # A stays, C moves 15 frames back
    assert p["probe"] == [(118, 286)]                                     # B's new span (120-284), with its margin
    # a changed file reaches every shot naming what it (or a file importing it) declares
    new2 = dict(new, files={"v/a.tsx": "2", "v/kit.tsx": "1"}, imports={"v/a.tsx": ["v/kit.tsx"], "v/kit.tsx": []},
                decl={"v/a.tsx": ["Receipt"], "v/kit.tsx": ["Card"]}, shots=[dict(s, sig=s["sig"].rstrip("2")) for s in new["shots"]])
    old2 = dict(old, files={"v/a.tsx": "1", "v/kit.tsx": "1"}, shots=[dict(s) for s in old["shots"]])
    old2["shots"][1] = dict(old2["shots"][1], end=4.75)
    old2["shots"][2] = dict(old2["shots"][2], at=4.75, end=9.75)
    p = reprobe.plan(None, old2, new2)
    assert p["probe"] == [(118, 286)] and p["why"]["reached_by_files"] == 1   # only B names Receipt
    p = reprobe.plan(None, old, dict(new, files={"src/gate.tsx": "x"}))
    assert p["full"] and "probe itself" in p["full"]


def test_kit3_row_read_by_its_attribute(tmp_path):
    """kit3's cut-outs keep their transparent margins: the row is the one the kit names (rw), not boxes on one floor"""
    gate.FRAME[:] = [W, H]
    a = item("img", "nope_a.png", 500, 300, 300, 420, rw=0)       # different heights and floors: the old grouping saw no row
    b = item("img", "nope_b.png", 900, 340, 260, 360, rw=0)
    rows = gate.row_groups([a, b], tmp_path, W, H)
    assert len(rows) == 1 and rows[0]["n"] == 2
    assert abs(rows[0]["off"] - ((500 + 1160) / 2 - W / 2)) < 1e-6   # its content's centre against the frame's


def test_same_frame_tolerates_float_noise_not_a_move():
    a = ['layout|{"frame":5,"items":[{"k":"img","t":"a.png","x":10.0,"y":5.0,"w":100.0,"h":50.0,"op":1,"c":0}]}']
    b = ['layout|{"frame":9,"items":[{"k":"img","t":"a.png","x":10.1,"y":5.0,"w":100.2,"h":50.0,"op":1,"c":0}]}']
    c = ['layout|{"frame":9,"items":[{"k":"img","t":"a.png","x":12.0,"y":5.0,"w":100.0,"h":50.0,"op":1,"c":0}]}']
    assert reprobe.same_frame(a, b) and not reprobe.same_frame(a, b, exact=True)
    assert not reprobe.same_frame(a, c)
    assert reprobe.join_close([(0, 10), (100, 200), (500, 600)], 150) == [(0, 200), (500, 600)]


def test_scope_ranges_widen_to_whole_shots():
    """the scoped gate: ranges merged, each widened to the shots it touches (a shot is checked whole), the film's end held"""
    assert gate.parse_scope("300-400, 100-200,150-250") == [(100, 250), (300, 400)]
    shots = [{"at": 0.0, "end": 2.0}, {"at": 2.0, "end": 5.0}, {"at": 5.0, "end": 9.0}]     # frames 0-119, 120-299, 300-539
    assert gate.widen_to_shots([(130, 140)], shots, 540) == [(120, 299)]
    assert gate.widen_to_shots([(100, 310), (500, 900)], shots, 540) == [(0, 539)]
    try:
        gate.widen_to_shots([(600, 700)], shots, 540)
        assert False, "a range past the film's end must stop the run"
    except SystemExit:
        pass
    assert gate.merge_spans([(0, 10), (100, 200)], 150) == [(0, 200)] and gate.merge_spans([(0, 10), (12, 20)]) == [(0, 10), (12, 20)]


def test_twice_scope_keeps_pairs_with_a_play_in_it():
    """--scope: a TWICE pair counts when either showing is in the scope, though the flag sits on the later one; without a scope the
    check is the full gate's own (the same flags)"""
    plays = [{"src": "v/clips/a.mp4", "f0": 100, "f1": 159, "s0": 1.0, "s1": 1.98, "n": 60},
             {"src": "v/clips/a.mp4", "f0": 5000, "f1": 5059, "s0": 1.0, "s1": 1.98, "n": 60},
             {"src": "v/clips/b.mp4", "f0": 9000, "f1": 9059, "s0": 0.0, "s1": 0.98, "n": 60},
             {"src": "v/clips/b.mp4", "f0": 9500, "f1": 9559, "s0": 0.0, "s1": 0.98, "n": 60}]
    lay = {f: [item("clip", p["src"], 0, 0, W, H)] for p in plays for f in [(p["f0"] + p["f1"]) // 2]}
    full = gate.check_twice(plays, lay, {})
    assert [f["at"] for f in full] == [5000, 9500]
    assert gate.check_twice(plays, lay, {}, scope=None) == full
    mine = gate.check_twice(plays, lay, {}, scope=[(90, 170)])
    assert [f["at"] for f in mine] == [5000]                          # the earlier showing is in the scope, the flag on the later one
    assert gate.check_twice(plays, lay, {}, scope=[(3000, 4000)]) == []
