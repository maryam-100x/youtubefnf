"""heavy.py: heavy jobs take turns across every chat on the computer."""
import json
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import heavy  # noqa: E402


def setup(tmp_path, monkeypatch, tickets, procs, commit_gb=40):
    monkeypatch.setattr(heavy, "DIR", tmp_path)
    monkeypatch.setattr(heavy, "GATE", tmp_path / ".gate")
    monkeypatch.setattr(heavy, "memory", lambda: (8.0, commit_gb, 50.0))
    for t in tickets:
        (tmp_path / f"{t['pid']}.json").write_text(json.dumps(t), encoding="utf-8")
    return procs


def ticket(pid, kind, exe="python.exe"):
    return {"pid": pid, "exe": exe, "what": f"{kind} {pid}", "kind": kind, "need_gb": heavy.NEED_GB[kind], "started": "x"}


def test_stale_tickets_go(tmp_path, monkeypatch):
    procs = setup(tmp_path, monkeypatch, [ticket(11, "cutout"), ticket(12, "finish")], {12: "notepad.exe"})
    assert heavy.tickets(procs) == [] and not list(tmp_path.glob("*.json"))   # 11 died, 12's pid is another program now


def test_two_cutouts_never_together(tmp_path, monkeypatch):
    procs = setup(tmp_path, monkeypatch, [ticket(11, "cutout")], {11: "python.exe"})
    assert "another cut-out" in heavy.blocker("cutout", 20, procs)
    assert heavy.blocker("finish", 4, procs) is None                       # 24 GB: inside the budget
    assert "render" in heavy.blocker("render", 10, procs) or "cutout" in heavy.blocker("render", 10, procs)


def test_a_render_runs_alone(tmp_path, monkeypatch):
    procs = setup(tmp_path, monkeypatch, [ticket(11, "render", "node.exe")], {11: "node.exe", 50: heavy.HEADLESS})
    for kind in ("cutout", "finish", "score", "render"):
        assert heavy.blocker(kind, heavy.NEED_GB[kind], procs)


def test_another_tools_remotion_and_low_memory_block(tmp_path, monkeypatch):
    procs = setup(tmp_path, monkeypatch, [], {50: heavy.HEADLESS})
    assert heavy.HEADLESS in heavy.blocker("finish", 4, procs)
    monkeypatch.setattr(heavy, "WINDOWS", True)   # Windows' commit check, on any computer
    procs = setup(tmp_path, monkeypatch, [], {}, commit_gb=10)
    assert "commit" in heavy.blocker("cutout", 20, procs) and heavy.blocker("finish", 4, procs) is None


def test_on_a_mac_the_memory_pressure_level_decides(tmp_path, monkeypatch):
    monkeypatch.setattr(heavy, "WINDOWS", False)
    procs = setup(tmp_path, monkeypatch, [], {}, commit_gb=1)   # the commit numbers are not read on a Mac
    level = {"v": "1"}
    monkeypatch.setattr(heavy, "_sysctl", lambda name: level["v"] if name == "kern.memorystatus_vm_pressure_level" else None)
    assert heavy.blocker("cutout", 20, procs) is None
    level["v"] = "2"
    assert "warning memory pressure" in heavy.blocker("cutout", 20, procs)
    level["v"] = "4"
    assert "critical" in heavy.blocker("finish", 4, procs)


def test_job_holds_and_drops_its_ticket(tmp_path, monkeypatch):
    setup(tmp_path, monkeypatch, [], {})
    monkeypatch.setattr(heavy, "processes", lambda: {os.getpid(): "python.exe"})
    with heavy.HeavyJob("test", "score", wait_minutes=0):
        t = json.loads((tmp_path / f"{os.getpid()}.json").read_text(encoding="utf-8"))
        assert t["kind"] == "score" and t["need_gb"] == 4
    assert not list(tmp_path.glob("*.json")) and not (tmp_path / ".gate").exists()
