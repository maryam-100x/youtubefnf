"""pipe.render_parts' orchestration: a lost-frame clip is re-encoded and its part tried again, a failing part steps its
concurrency down and goes on, a kit3 refusal stops with its reason, done parts stay done. render_parts.mjs is replaced by a fake that
answers with its machine lines (DONE/FAIL), so no Remotion runs."""
import subprocess
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import pipe  # noqa: E402


class FakeV:
    def __init__(self, tmp):
        self.comp = "V"
        self.pub = tmp / "pub"
        self.pipe_dir = tmp / "pipe"
        self.render_dir = tmp / "render"


def fake_runs(script, tmp, monkeypatch, cores=16):
    """script: a list of functions (job) -> stdout, one per render_parts.mjs run; parts reported DONE get a file of the right frames.
    cores: the computer's CPU cores as pipe sees them (the tests never depend on the computer running them)"""
    calls = []
    monkeypatch.setattr(pipe, "_cores", lambda: cores)

    def run_watched(cmd, cwd, env, log, stall=300):
        import json
        job = json.loads(Path(cmd[2]).read_text(encoding="utf-8"))
        calls.append(job)
        out = script[len(calls) - 1](job)
        for ln in out.splitlines():
            if ln.startswith("DONE "):
                i = int(ln.split()[1])
                p = next(p for p in job["parts"] if p["i"] == i)
                Path(p["file"]).write_bytes(b"x")
        r = subprocess.CompletedProcess(cmd, 0 if all(ln.startswith(("DONE", "ENC", "COMP", "PROGRESS")) for ln in out.splitlines() if ln) else 3, out, "")
        r.stalled = False
        return r
    monkeypatch.setattr(pipe, "run_watched", run_watched)
    monkeypatch.setattr(pipe, "gpu_guard", lambda gl, since: None)
    monkeypatch.setattr(pipe.time, "sleep", lambda s: None)
    sizes = {}
    monkeypatch.setattr(pipe, "frame_count", lambda p: sizes.get(Path(p).name, 100))
    return calls


SETTINGS = {"crf": 14, "preset": "veryfast", "imageFormat": "jpeg", "jpegQuality": 92, "parallel": "force", "gl": "angle", "scale": 1.0, "timeoutMs": 1000}
PARTS = [(0, 0, 99), (1, 100, 199), (2, 200, 299)]


def test_lost_frame_reencodes_the_clip_and_goes_on(tmp_path, monkeypatch):
    v = FakeV(tmp_path)
    tmp_path.joinpath("render").mkdir()
    done = []
    script = [lambda job: "DONE 0 100 5.0\nFAIL 1 Compositor error: No frame found at position 58500 for source C:\\Studio\\tmp\\remotion-v4.0.532-assets\\c34b.mp4 (original source = http://localhost:3000/public/v12/clips/c34b.mp4)",   # Remotion's real shape: its temp copy first, the clip in "original source"
              lambda job: "\n".join(f"DONE {p['i']} 100 5.0" for p in job["parts"])]
    calls = fake_runs(script, tmp_path, monkeypatch)
    re_enc = []
    monkeypatch.setattr(pipe, "reencode_clip", lambda v_, rel, log: re_enc.append(rel) or True)
    pipe.render_parts(v, None, "bundle", SETTINGS, PARTS, 8, tmp_path / "render", 0, lambda i, f0, f1, s, c: done.append((i, c)))
    assert re_enc == ["v12/clips/c34b.mp4"]
    assert [p["i"] for p in calls[1]["parts"]] == [1, 2] and calls[1]["concurrency"] == 8   # the rest at the video's concurrency
    assert done == [(0, 8), (1, 8), (2, 8)]


def test_a_failing_part_steps_down_then_the_rest_go_on(tmp_path, monkeypatch):
    v = FakeV(tmp_path)
    done = []
    script = [lambda job: "FAIL 0 Target closed",
              lambda job: "FAIL 0 Target closed",
              lambda job: "DONE 0 100 9.0",
              lambda job: "\n".join(f"DONE {p['i']} 100 5.0" for p in job["parts"])]
    calls = fake_runs(script, tmp_path, monkeypatch)
    pipe.render_parts(v, None, "bundle", SETTINGS, PARTS, 8, tmp_path, 0, lambda i, f0, f1, s, c: done.append((i, c)))
    assert [c["concurrency"] for c in calls] == [8, 4, 2, 8]
    assert [len(c["parts"]) for c in calls] == [3, 1, 1, 2]   # a part retried low goes alone
    assert done == [(0, 2), (1, 8), (2, 8)]


def test_a_computer_with_few_cores_renders_at_its_cores_and_still_steps_down(tmp_path, monkeypatch):
    v = FakeV(tmp_path)
    done = []
    script = [lambda job: "FAIL 0 Target closed",
              lambda job: "FAIL 0 Target closed",
              lambda job: "DONE 0 100 9.0",
              lambda job: "\n".join(f"DONE {p['i']} 100 5.0" for p in job["parts"])]
    calls = fake_runs(script, tmp_path, monkeypatch, cores=3)
    pipe.render_parts(v, None, "bundle", SETTINGS, PARTS, 8, tmp_path, 0, lambda i, f0, f1, s, c: done.append((i, c)))
    assert [c["concurrency"] for c in calls] == [3, 2, 1, 3]   # Remotion refuses more than the cores; each retry lower still
    assert [len(c["parts"]) for c in calls] == [3, 1, 1, 2]
    assert done == [(0, 1), (1, 3), (2, 3)]
    monkeypatch.setattr(pipe, "_cores", lambda: 3)
    assert pipe.cap_conc(6) == 3 and pipe.cap_conc(2) == 2 and pipe.cap_conc(None) is None


def test_a_part_failing_every_way_stops_the_line(tmp_path, monkeypatch):
    v = FakeV(tmp_path)
    fake_runs([lambda job: "FAIL 0 Target closed"] * 5, tmp_path, monkeypatch)
    with pytest.raises(SystemExit, match="part 0 .* failed"):
        pipe.render_parts(v, None, "bundle", SETTINGS, PARTS[:1], 8, tmp_path, 0, lambda *x: None)


def test_a_kit3_refusal_stops_with_its_reason(tmp_path, monkeypatch):
    v = FakeV(tmp_path)
    fake_runs([lambda job: "FAIL 0 kit3 Page v/p.png: mark 1 holds 78% of its crop's ink: the crop is only that thing"], tmp_path, monkeypatch)
    with pytest.raises(SystemExit, match="kit3 piece refused"):
        pipe.render_parts(v, None, "bundle", SETTINGS, PARTS[:1], 8, tmp_path, 0, lambda *x: None)


def test_plan_parts_covers_every_frame_once():
    plan = pipe.plan_parts(188182, 3000)
    assert plan[0][1] == 0 and plan[-1][2] == 188181
    assert all(b[1] == a[2] + 1 for a, b in zip(plan, plan[1:]))
    assert len(plan) == 63
