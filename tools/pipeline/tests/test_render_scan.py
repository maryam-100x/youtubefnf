"""qa_render_scan.py: small clips made with ffmpeg's lavfi sources, each with one known render-time fault, must be flagged; a clean clip
must not. The base picture is lavfi's mandelbrot (a slow zoom: every frame moves a little, corr between frames ~0.997, mean Y ~110-145);
the foreign picture is testsrc2."""
import json
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import qa_render_scan as q  # noqa: E402

pytestmark = pytest.mark.skipif(not shutil.which("ffmpeg") or not shutil.which("ffprobe"), reason="ffmpeg/ffprobe not on PATH")

N = 180   # 3 s at 60 fps


def ffmpeg(*args):
    subprocess.run(["ffmpeg", "-nostdin", "-v", "error", "-y", *args], check=True)


def enc(out):
    return ["-frames:v", str(N), "-c:v", "libx264", "-preset", "ultrafast", "-crf", "18", "-pix_fmt", "yuv420p", str(out)]


@pytest.fixture(scope="module")
def clips(tmp_path_factory):
    d = tmp_path_factory.mktemp("clips")
    base = ["-f", "lavfi", "-i", "mandelbrot=s=320x180:r=60"]
    c = {}
    c["clean"] = d / "clean.mkv"
    ffmpeg(*base, *enc(c["clean"]))
    c["black"] = d / "black.mkv"        # frames 90-91 black
    ffmpeg(*base, "-vf", "drawbox=x=0:y=0:w=iw:h=ih:color=black@1:t=fill:enable='between(n,90,91)'", *enc(c["black"]))
    c["foreign"] = d / "foreign.mkv"    # frame 120 another picture
    ffmpeg(*base, "-f", "lavfi", "-i", "testsrc2=s=320x180:r=60", "-filter_complex", "[0][1]overlay=enable='eq(n,120)'", *enc(c["foreign"]))
    c["frozen"] = d / "frozen.mkv"      # frames 60-100 hold frame 59
    ffmpeg(*base, "-filter_complex", "[0]split[a][b];[a][b]freezeframes=first=60:last=100:replace=59", *enc(c["frozen"]))
    # the source the probe names for the frozen test: the clean picture as an mp4 in a public dir
    pub = d / "pub"
    (pub / "clips").mkdir(parents=True)
    ffmpeg(*base, "-frames:v", str(N), "-c:v", "libx264", "-preset", "ultrafast", "-crf", "18", "-pix_fmt", "yuv420p", str(pub / "clips" / "src.mp4"))
    c["pub"] = pub
    return c


def probe(path, lit_frames=range(N)):
    """a probe like the gate's: the clip clips/src.mp4 full frame on every frame of lit_frames (source second = film second), nothing
    on the others"""
    lines = []
    for f in range(N):
        items = []
        if f in lit_frames:
            items = [{"k": "clip", "t": "clips/src.mp4", "x": 0, "y": 0, "w": 1920, "h": 1080, "cx0": 0, "cy0": 0, "cx1": 1920, "cy1": 1080,
                      "op": 1, "br": 1, "fs": 0, "e": 0, "c": 0, "pa": -1, "g": ""}]
            lines.append("clip|" + json.dumps({"abs": f, "src": "clips/src.mp4", "f": f, "s": f / 60, "start": 0, "rate": 1}))
        lines.append("layout|" + json.dumps({"frame": f, "W": 1920, "H": 1080, "items": items, "ats": []}))
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return path


def run(clip, tmp_path, probe_path=None, pub=None, **kw):
    return q.scan([(clip, 0)], probe_path, tmp_path / "out", 60, pub, **kw)


def test_clean_clip_no_flag(clips, tmp_path):
    assert run(clips["clean"], tmp_path) == []
    assert run(clips["clean"], tmp_path, probe(tmp_path / "p.jsonl"), clips["pub"]) == []


def test_black_frames_flagged(clips, tmp_path):
    flags = run(clips["black"], tmp_path)
    assert [(x["check"], x["at"], x["to"]) for x in flags] == [("BLACK_DIP", 90, 91)]
    assert Path(flags[0]["strip"]).exists() and Path(flags[0]["strip"]).name == "BLACK_DIP_90.png"
    # the probe says the clip is lit there: a render fault
    flags = run(clips["black"], tmp_path, probe(tmp_path / "p.jsonl"), clips["pub"])
    assert [(x["check"], x["at"]) for x in flags] == [("BLACK_DIP", 90)] and "render time" in flags[0]["what"]


def test_probe_dropout_is_no_alibi(clips, tmp_path):
    # the probe also shows nothing at 90-91, with hard edges: the composition dropping out (a mount race reaches the probe too), not
    # a designed cut, so it stays a flag
    p = probe(tmp_path / "p.jsonl", lit_frames=[f for f in range(N) if f not in (90, 91)])
    flags = run(clips["black"], tmp_path, p, clips["pub"])
    assert [(x["check"], x["at"]) for x in flags] == [("BLACK_DIP", 90)] and "probe shows nothing there either" in flags[0]["what"]


def test_designed_fade_passes(clips, tmp_path):
    # a dip to black by design: the probe's opacity falls over 84-89 and climbs back over 92-97, black at 90-91 (nothing lit)
    lines = []
    for f in range(N):
        op = 1.0 if f < 84 or f > 97 else max(0.0, (89 - f) / 6) if f <= 89 else 0.0 if f <= 91 else (f - 91) / 6
        items = [] if op < 0.05 else [{"k": "clip", "t": "clips/src.mp4", "x": 0, "y": 0, "w": 1920, "h": 1080, "cx0": 0, "cy0": 0, "cx1": 1920,
                                       "cy1": 1080, "op": round(op, 2), "br": 1, "fs": 0, "e": 0, "c": 0, "pa": -1, "g": ""}]
        if items:
            lines.append("clip|" + json.dumps({"abs": f, "src": "clips/src.mp4", "s": f / 60}))
        lines.append("layout|" + json.dumps({"frame": f, "W": 1920, "H": 1080, "items": items, "ats": []}))
    p = tmp_path / "fade.jsonl"
    p.write_text("\n".join(lines) + "\n", encoding="utf-8")
    assert run(clips["black"], tmp_path, p, clips["pub"]) == []


def test_foreign_frame_flagged(clips, tmp_path):
    flags = run(clips["foreign"], tmp_path)
    assert [(x["check"], x["at"], x["to"]) for x in flags] == [("FLASH_FRAME", 120, 120)]
    assert "inside a shot" in flags[0]["what"]


def test_foreign_frame_in_a_cut_flagged(clips, tmp_path):
    # A (mandelbrot) | one testsrc2 frame | B (mandelbrot turned upside down): a third picture squeezed into a cut
    d = tmp_path
    a, b = d / "a.mkv", d / "b.mkv"
    ffmpeg("-f", "lavfi", "-i", "mandelbrot=s=320x180:r=60", "-f", "lavfi", "-i", "testsrc2=s=320x180:r=60", "-filter_complex",
           "[0]split[m0][m1];[m1]vflip,hue=h=120[v];[m0][v]overlay=enable='gte(n,91)'[ab];[ab][1]overlay=enable='eq(n,90)'", *enc(a))
    flags = q.scan([(a, 0)], None, d / "out", 60)
    assert [(x["check"], x["at"]) for x in flags] == [("FLASH_FRAME", 90)] and "in a cut" in flags[0]["what"]
    # the same cut without the stray: clean
    ffmpeg("-f", "lavfi", "-i", "mandelbrot=s=320x180:r=60", "-filter_complex", "[0]split[m0][m1];[m1]vflip,hue=h=120[v];[m0][v]overlay=enable='gte(n,90)'", *enc(b))
    assert q.scan([(b, 0)], None, d / "out2", 60) == []


def test_frozen_stretch_flagged(clips, tmp_path):
    p = probe(tmp_path / "p.jsonl")
    flags = run(clips["frozen"], tmp_path, p, clips["pub"])
    assert [x["check"] for x in flags] == ["FROZEN"]
    # (x264 refines the first repeats of the held frame for a few frames: the stillness it measures starts at 59-66)
    assert 58 <= flags[0]["at"] <= 68 and 99 <= flags[0]["to"] <= 101
    # no probe: a freeze can't be told from still footage, so it isn't flagged
    assert run(clips["frozen"], tmp_path / "np") == []


def test_still_source_is_not_frozen(clips, tmp_path):
    # the probe holds the source on one second (a freeze in the source itself): the frozen render is right
    lines = []
    for f in range(N):
        items = [{"k": "clip", "t": "clips/src.mp4", "x": 0, "y": 0, "w": 1920, "h": 1080, "cx0": 0, "cy0": 0, "cx1": 1920, "cy1": 1080,
                  "op": 1, "br": 1, "fs": 0, "e": 0, "c": 0, "pa": -1, "g": ""}]
        s = 59 / 60 if 60 <= f <= 100 else f / 60
        lines.append("clip|" + json.dumps({"abs": f, "src": "clips/src.mp4", "s": s}))
        lines.append("layout|" + json.dumps({"frame": f, "W": 1920, "H": 1080, "items": items, "ats": []}))
    p = tmp_path / "held.jsonl"
    p.write_text("\n".join(lines) + "\n", encoding="utf-8")
    assert run(clips["frozen"], tmp_path, p, clips["pub"]) == []


def test_frames_count_flagged(clips, tmp_path):
    flags = q.scan([(clips["clean"], 0)], None, tmp_path / "out", 60, expected=[N + 2])
    assert [x["check"] for x in flags] == ["FRAMES"] and f"holds {N} frames" in flags[0]["what"]


def test_pieces_join(clips, tmp_path):
    # two pieces of one film: the black frames sit right at the join (the second piece starts on them)
    # (cut from lavfi by frame number: re-cutting an MKV by time duplicates a frame at its millisecond timestamps)
    a, b = tmp_path / "p0.mkv", tmp_path / "p1.mkv"
    box = "drawbox=x=0:y=0:w=iw:h=ih:color=black@1:t=fill:enable='between(n,90,91)'"
    ffmpeg("-f", "lavfi", "-i", "mandelbrot=s=320x180:r=60", "-vf", f"{box},trim=end_frame=90", *enc(a)[2:])
    ffmpeg("-f", "lavfi", "-i", "mandelbrot=s=320x180:r=60", "-vf", f"{box},trim=start_frame=90:end_frame=180,setpts=PTS-STARTPTS", *enc(b)[2:])
    flags = q.scan([(a, 0), (b, 90)], None, tmp_path / "out", 60, expected=[90, 90])
    assert [(x["check"], x["at"], x["to"]) for x in flags] == [("BLACK_DIP", 90, 91)]
    # the second piece one frame short of its share
    flags = q.scan([(a, 0), (b, 90)], None, tmp_path / "out2", 60, expected=[90, 91])
    assert [x["check"] for x in flags if x["check"] == "FRAMES"] == ["FRAMES"]


def clip_probe(path, plays):
    """a probe of full-frame clips: plays = [(first_frame, last_frame, name, source second at first_frame)]"""
    lines = []
    for f0, f1, name, s0 in plays:
        for f in range(f0, f1 + 1):
            it = {"k": "clip", "t": f"clips/{name}", "x": 0, "y": 0, "w": 1920, "h": 1080, "cx0": 0, "cy0": 0, "cx1": 1920, "cy1": 1080,
                  "op": 1, "br": 1, "fs": 0, "e": 0, "c": 0, "pa": -1, "g": ""}
            lines.append("clip|" + json.dumps({"abs": f, "src": f"clips/{name}", "s": s0 + (f - f0) / 60}))
            lines.append("layout|" + json.dumps({"frame": f, "W": 1920, "H": 1080, "items": [it], "ats": []}))
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return path


def test_source_edge_stray_flagged(clips, tmp_path):
    # a clip that opens on 3 frames of its source's previous shot (here testsrc2) before its own picture
    pub = clips["pub"]
    b = pub / "clips" / "b.mp4"
    ffmpeg("-f", "lavfi", "-i", "mandelbrot=s=320x180:r=60", "-f", "lavfi", "-i", "testsrc2=s=320x180:r=60", "-filter_complex",
           "[0]vflip,hue=h=120[v];[v][1]overlay=enable='lt(n,3)'", "-frames:v", "90", "-c:v", "libx264", "-preset", "ultrafast",
           "-crf", "18", "-pix_fmt", "yuv420p", str(b))
    film = tmp_path / "film.mkv"
    ffmpeg("-i", str(pub / "clips" / "src.mp4"), "-i", str(b), "-filter_complex",
           "[0]trim=end_frame=90,setpts=PTS-STARTPTS[x];[1]trim=end_frame=90,setpts=PTS-STARTPTS[y];[x][y]concat=n=2:v=1", *enc(film)[2:])
    p = clip_probe(tmp_path / "p.jsonl", [(0, 89, "src.mp4", 0.0), (90, 179, "b.mp4", 0.0)])
    flags = q.scan([(film, 0)], p, tmp_path / "out", 60, pub)
    assert [(x["check"], x["at"], x["to"]) for x in flags] == [("FLASH_FRAME", 90, 92)]
    assert "source's own cut at the play's edge" in flags[0]["what"]


def test_source_flash_mid_play_passes(clips, tmp_path):
    # the same 3 frames inside the footage, mid-play (a camera flash, a promo's own quick cut): the footage's own with a probe
    pub = clips["pub"]
    m = pub / "clips" / "mid.mp4"
    ffmpeg("-f", "lavfi", "-i", "mandelbrot=s=320x180:r=60", "-f", "lavfi", "-i", "testsrc2=s=320x180:r=60", "-filter_complex",
           "[0][1]overlay=enable='between(n,100,102)'", "-frames:v", str(N), "-c:v", "libx264", "-preset", "ultrafast", "-crf", "18",
           "-pix_fmt", "yuv420p", str(m))
    film = tmp_path / "film.mkv"
    ffmpeg("-i", str(m), *enc(film))
    p = clip_probe(tmp_path / "p.jsonl", [(0, N - 1, "mid.mp4", 0.0)])
    assert q.scan([(film, 0)], p, tmp_path / "out", 60, pub) == []
    # without a probe it can't be told from a fault: flagged
    assert [(x["check"], x["at"]) for x in q.scan([(film, 0)], None, tmp_path / "out2", 60)] == [("FLASH_FRAME", 100)]
