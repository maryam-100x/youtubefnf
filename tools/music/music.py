"""Music made in code: one command for every step (standard/MUSIC.md has the method, the bar and the order).

    SYNTH tools/music/music.py render <film.py> [--words words.json] [--out DIR] [--beds O,G | all] [--stems] [--judge]
        every bed of a video from its narration's word times: rendered, checked, written where the cue sheet reads it.
        A video's film file is videos/<video>/score/music.py: its words default to the video's tools/motion/src/<src>/words.json
        (video.toml [video] src) and its beds go to MEDIA/videos/<video>/build/music/. Run it again after the voice changes: every
        anchor is looked up again by section and phrase, so every bed retimes to the new narration.
    SYNTH tools/music/music.py selftest [<film.py> <words.json>]     the logic, offline (no synth, no model): ALL OK
    SYNTH tools/music/music.py patches [substring]                   Surge XT's patches (proves its library is found)
    SYNTH tools/music/music.py audition <role> <out.json> ...        a role's patches measured alone, in bulk
    SYNTH tools/music/music.py pick <film.py> <bed> <t0> <t1> <cands.json> <out.json> --words <words.json>
                                                                     each part's sound chosen in context by the stand-in ear
    SYNTH tools/music/music.py check "<patch>" ... [--role bass]     a patch's real octave and the tones it adds
    SYNTH tools/music/music.py mixdown <stems dir> [part=dB ...] [--judge] [--out bed.wav --grid <bed>.wav.grid.json]
    SYNTH tools/music/music.py bands <wav> ... [--judge]             a bed against the bar
    SYNTH tools/music/music.py judge <wav> ... | --warm              the quality model's scores (--warm: download it, check it runs)
    SYNTH tools/music/music.py stand-in <words.json> <out.wav>       a speech-shaped test signal from word times (not speech)
    SYNTH tools/music/music.py ab <mixA.wav> <mixB.wav> <t0> <t1> <outdir>    a blind pair for the creator's ears

The beds go under the voice through the cue sheet (tools/sound/score.py, `code_beds(...)`): one mixer for every video, whatever made
its music. Checks printed by render, for every bed: each segment's real tempo and the change at each joint (flagged over 12%), every
anchor on a downbeat (within 1 ms), every event note on its word (within 5 ms), the band numbers, with --judge the scores, the
profile and the verdict. Exit code 1 when an anchor or an event is off.
"""
from __future__ import annotations

import argparse
import importlib
import importlib.util
import json
import sys
import time
import tomllib
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

from musickit.settings import REPO, SR, VIDEOS, out_dir, _paths  # noqa: E402
from musickit.writing import Words  # noqa: E402

TOOLS = {"selftest": "selftest", "patches": "surge", "audition": "audition", "pick": "pick", "check": "patch_check",
         "mixdown": "mixdown", "bands": "bands", "judge": "judge", "stand-in": "stand_in_voice", "ab": "ab_pair"}


def load_film(path: str):
    spec = importlib.util.spec_from_file_location("film", path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def video_of(film_path: Path) -> str | None:
    """The video a film file belongs to (videos/<video>/score/music.py), or None for a file elsewhere (the example)."""
    p = film_path.resolve()
    vids = (REPO / "videos").resolve()
    if p.parent.name == "score" and p.parent.parent.parent == vids:
        return p.parent.parent.name
    return None


def default_words(film, film_path: Path) -> Path:
    """A video's film file reads the video's own word times (a DEFAULT_WORDS copied over from the example is ignored there); a file
    elsewhere reads its DEFAULT_WORDS, beside it."""
    video = video_of(film_path)
    if not video and getattr(film, "DEFAULT_WORDS", None):
        return (film_path.resolve().parent / film.DEFAULT_WORDS).resolve()
    if video:
        toml = REPO / "videos" / video / "video.toml"
        src = tomllib.loads(toml.read_text(encoding="utf-8")).get("video", {}).get("src") if toml.exists() else None
        if not src:
            raise SystemExit(f"{toml}: no [video] src, so the word times can't be found: pass --words")
        return _paths.MOTION / "src" / src / "words.json"
    raise SystemExit("no word times: pass --words <words.json>")


def tempo_report(bed) -> tuple[list[float], list[float]]:
    segs = bed.clock.segs
    real = [60.0 * bpb * n / (t1 - t0) for t0, t1, n, bpb in segs]
    joints = [abs(b / a - 1) * 100 for a, b in zip(real, real[1:])]
    return real, joints


def render(argv):
    ap = argparse.ArgumentParser(prog="music.py render")
    ap.add_argument("film")
    ap.add_argument("--words", default="")
    ap.add_argument("--out", default="")
    ap.add_argument("--beds", default="all")
    ap.add_argument("--stems", action="store_true")
    ap.add_argument("--judge", action="store_true")
    a = ap.parse_args(argv)

    film_path = Path(a.film)
    film = load_film(str(film_path))
    words_path = Path(a.words) if a.words else default_words(film, film_path)
    W = Words(words_path)
    video = video_of(film_path)
    out = out_dir(a.out or (VIDEOS / video / "build" / "music" if video else None))
    secs = sorted({x["beat"] for x in W.W}, key=lambda s: W.first(s))
    print(f"{getattr(film, 'TITLE', film_path.name)}: {len(W.W)} words in {len(secs)} sections, last word ends {W.end():.2f} s "
          f"({words_path}) -> {out}", flush=True)
    which = list(film.BEDS) if a.beds == "all" else a.beds.split(",")
    if a.beds == "all":   # a full render replaces the old beds, so the cue sheet never picks up a bed the film no longer has
        for old in out.glob("bed_*.wav*"):
            if old.name.split(".")[0][4:] not in which:
                old.unlink()
    rep = {"film": str(film_path), "words": str(words_path), "beds": {}}
    started = time.time()
    sys.path.insert(0, str(REPO / "tools" / "pipeline"))
    from heavy import HeavyJob   # the beds take their turn with the other heavy jobs (never beside a video render)
    with HeavyJob(f"music beds {film_path.parent.parent.name}/{film_path.name}", "score"):
        failed = render_beds(a, film, W, which, out, rep, started)
    (out / "report.json").write_text(json.dumps(rep, indent=1), encoding="utf-8")
    print(f"\nreport -> {out / 'report.json'}  ({time.time() - started:.0f} s)")
    print("next: the cue sheet takes these beds with code_beds(...) (tools/sound/score.py), and the mix puts them under the voice")
    if failed:
        print("FAILED:", failed)
        sys.exit(1)


def render_beds(a, film, W, which, out, rep, started) -> list[str]:
    import numpy as np
    from musickit import bands
    from musickit.compose import render_bed
    from musickit.surge import Surge
    failed, surge = [], None
    for bid in which:
        bed = film.BEDS[bid](W)
        real, joints = tempo_report(bed)
        print(f"\nbed {bid} ({bed.key}): film {bed.t0:.3f}-{bed.t1:.3f} s, {len(bed.clock)} bars, written at {bed.bpm:.2f} bpm, "
              f"{sum(len(t.notes) for t in bed.tracks)} notes" + (", a loop" if bed.loop else ""), flush=True)
        print("  segments: " + ", ".join(f"{n} bars {r:.2f} bpm" for (t0, t1, n, _), r in zip(bed.clock.segs, real))
              + ("" if not joints else "; joints " + ", ".join(f"{j:.1f}%" for j in joints))
              + ("  <- a joint over 12%: move an anchor or the tempo, or listen there" if any(j > 12 for j in joints) else ""))
        if surge is None:
            print("  starting Surge XT (first start ~35 s, the first patch ~30 s more)...", flush=True)
            surge = Surge(sr=SR)
        wav = out / f"bed_{bid}.wav"
        info = {"bed": bid, "key": bed.key, "bpm": round(bed.bpm, 3), "note": bed.note,
                "anchors": {k: round(t, 4) for k, t in bed.anchors.items()},
                "events": {k: [tn, round(t, 4)] for k, (tn, t) in bed.events.items()}}
        mix = render_bed(bed.tracks, bed.t0, bed.t1, wav, tail=4.0, stems=(out / f"stems_{bid}") if a.stems else None,
                         clock=bed.clock, surge=surge, loop=bed.loop, info=info)
        grid = json.loads(Path(str(wav) + ".grid.json").read_text(encoding="utf-8"))
        downs = np.array(grid["downbeats"] + [bed.clock.end() - bed.t0]) + bed.t0   # + the bar line that ends the last bar
        anc = {k: round(float(np.min(np.abs(downs - t))) * 1000, 2) for k, t in bed.anchors.items()}
        bad_anc = [k for k, ms in anc.items() if ms > 1.0]
        ev = {}
        for k, (tname, t) in bed.events.items():
            tr = next(x for x in bed.tracks if x.name == tname)
            ev[k] = round(min(abs(n[0] - t) for n in tr.notes) * 1000, 2) if tr.notes else None
        bad_ev = [k for k, ms in ev.items() if ms is None or ms > 5.0]
        m = bands.measure(mix)
        j = prof = None
        if a.judge:
            from musickit import judge
            j = judge.score_array(mix.T, SR)
            prof = bands.profile(str(wav))
        ok, why = bands.verdict(m, j)
        print(f"  -> {wav.name}: {mix.shape[1] / SR:.1f} s  [{time.time() - started:.0f} s]")
        print(f"  anchors on downbeats (ms off): {anc}" + (f"  <- OFF: {bad_anc}" if bad_anc else "  ok"))
        if ev:
            print(f"  events on their words (ms off): {ev}" + (f"  <- OFF: {bad_ev}" if bad_ev else "  ok"))
        print(f"  bands: {m['lt1k']}% under 1 kHz, {m['voice_band']}% in 1-4 kHz, {m['sub']}% under 80 Hz, centroid {m['centroid']} Hz")
        if j:
            print(f"  judge: PQ {j['PQ']} (min {j['PQ_min']}), CE {j['CE']}, CU {j['CU']}, PC {j['PC']} [{j['windows']} windows]")
            print(f"  profile: {prof['onsets_s']} onsets a second, loudest minus quietest 8-s block {prof['range_8s_db']} dB, "
                  f"frame centroid {prof['centroid_med']} Hz (reported)")
        print("  " + (("AT THE BAR" if a.judge else "bands at the bar (run --judge for the full verdict)") if ok
                      else "UNDER THE BAR: " + "; ".join(why)), flush=True)
        failed += [f"bed {bid}: anchor {k}" for k in bad_anc] + [f"bed {bid}: event {k}" for k in bad_ev]
        rep["beds"][bid] = {"wav": str(wav), "t0": bed.t0, "t1": bed.t1, "key": bed.key, "bpm_written": bed.bpm,
                            "segment_bpm": [round(r, 3) for r in real], "joint_change_pct": [round(x, 2) for x in joints],
                            "anchors_ms_off": anc, "events_ms_off": ev, "bands": m, "judge": j, "profile": prof, "at_the_bar": ok,
                            "why_not": why}
    return failed


def main():
    if len(sys.argv) < 2 or sys.argv[1] in ("-h", "--help"):
        raise SystemExit(__doc__)
    cmd, rest = sys.argv[1], sys.argv[2:]
    if cmd == "render":
        return render(rest)
    if cmd not in TOOLS:
        raise SystemExit(f"unknown command {cmd!r}\n\n{__doc__}")
    mod = importlib.import_module(f"musickit.{TOOLS[cmd]}")
    sys.argv = [f"music.py {cmd}"] + rest
    if cmd == "patches":
        print("\n".join(mod.list_patches(rest[0] if rest else "")))
        return
    mod.main()


if __name__ == "__main__":
    main()
