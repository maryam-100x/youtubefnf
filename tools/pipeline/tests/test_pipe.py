"""The production line's tests: the generic steps' own pieces on synthetic inputs (a video folder in a temp dir, fake logs).

  PIPE -m pytest tools/pipeline/tests/test_pipe.py -q"""
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))
import common  # noqa: E402
import pipe  # noqa: E402


def test_chunk_edges_cover_the_film():
    total = round(553.133 * 60)
    assert pipe.chunk_edges(total, 10) == [round(total * i / 10) for i in range(11)]
    assert pipe.chunk_edges(total, 10)[0] == 0 and pipe.chunk_edges(total, 10)[-1] == total


def make_video(tmp_path, folder, toml):
    d = tmp_path / folder
    d.mkdir()
    (d / "video.toml").write_text(toml, encoding="utf-8")
    return d


def test_video_toml_defaults(tmp_path):
    d = make_video(tmp_path, "012-city-at-night", '[video]\ncomp = "V12"\nsrc = "v12"\nframes = 600\n\n[render]\nconcurrency = 8\n')
    v = common.Video(common.find_video(str(d)))
    assert (v.id, v.kind, v.comp, v.src, v.module) == ("012", "long", "V12", "v12", "V12.tsx")
    assert v.pub == common.MEDIA / "pub012" and v.dj == common.VIDEOS / "012-city-at-night"
    assert v.chunks == 10 and v.concurrency == 8 and v.gl == "angle"
    assert v.export_name(2) == "012-city-at-night_v2"   # name defaults to the folder's slug, plus the version
    assert v.duration() == 10.0 and v.frames() == 600   # [video] frames wins over the beats
    assert v.pipe_dir == v.dj / "pipeline"


def test_video_toml_short_from_the_folder_name(tmp_path):
    d = make_video(tmp_path, "013-short-night-market", '[video]\nid = "013"\ncomp = "Short13"\nsrc = "s13"\nframes = 3000\n')
    v = common.Video(common.find_video(str(d / "video.toml")))
    assert v.kind == "short" and v.id == "013" and abs(v.duration() - 50.0) < 1e-9


def test_rescue_in_progress(tmp_path):
    out = tmp_path / "part_00.mkv"
    log = tmp_path / "part_00.log"
    tmp = tmp_path / "part_00.mkv.abc123.remotion-in-progress"
    tmp.write_bytes(b"x" * 10)
    log.write_text("... Encoded 120 frames ...", encoding="utf-8")
    assert pipe.rescue_in_progress(out, log) and out.exists() and not tmp.exists()
    out2, log2 = tmp_path / "part_01.mkv", tmp_path / "part_01.log"
    (tmp_path / "part_01.mkv.def.remotion-in-progress").write_bytes(b"x")
    log2.write_text("crashed", encoding="utf-8")
    assert not pipe.rescue_in_progress(out2, log2) and not out2.exists()


def test_lock_is_advisory_and_stale_locks_die(tmp_path, monkeypatch):
    monkeypatch.setattr(common, "LOCK", tmp_path / "remotion.lock")
    (tmp_path / "remotion.lock").write_text(json.dumps({"pid": 999999, "what": "old", "started": "x"}), encoding="utf-8")
    assert common.read_lock() is None and not (tmp_path / "remotion.lock").exists()
