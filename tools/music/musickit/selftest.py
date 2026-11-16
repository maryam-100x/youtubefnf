"""Offline checks of the method's logic (no Surge XT, no model, no audio packages): run after installing, after any change to
compose/writing, and on every new film file before its first render.

    SYNTH tools/music/music.py selftest [<film.py> <words.json>]     (no arguments: the example film)

1. Clock: every segment starts on a downbeat at its anchor time, bars inside a segment are equal.
2. Chords: symbols parse; voice leading moves less than jumping to the nearest root position.
3. Word lookups: first / word / last_end on the example's word times.
4. The film (default: the example): every bed builds, every anchor is a downbeat, every event note is on its word, notes are in
   MIDI range, and no two beds play at once.
"""
from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

from .compose import Clock, chord, close_voicings, lead, voicing
from .writing import Words, clock, fit_bpm, prog, seg_bpms


def check(cond, what):
    print(("  ok   " if cond else "  FAIL ") + what)
    return bool(cond)


def main():
    ok = True
    print("clock")
    clk, fb = clock([0.0, 12.8, 29.2, 37.2], 96)
    downs = [s for s, L, b in clk.bars]
    for t, b in zip([0.0, 12.8, 29.2], fb):
        ok &= check(abs(clk.t(b) - t) < 1e-9, f"anchor {t} is the downbeat of bar {b}")
    ok &= check(abs(clk.end() - 37.2) < 1e-9, "the last bar ends on the last anchor")
    ok &= check(len(downs) == fb[-1], f"{len(downs)} bars")
    bp = fit_bpm([0.0, 12.8, 29.2, 37.2], 92, 100)
    s = seg_bpms([0.0, 12.8, 29.2, 37.2], bp)
    ok &= check(max(abs(x / bp - 1) for x in s) < 0.06, f"fit_bpm {bp}: segments {[round(x, 2) for x in s]}")
    print("chords")
    ok &= check(chord("Gm") == (7, (0, 3, 7)) and chord("Ebmaj7") == (3, (0, 4, 7, 11)), "symbols parse")
    ok &= check(voicing("Am", 52, 71) == [57, 60, 64], f"Am in 52-71: {voicing('Am', 52, 71)}")
    prev = lead(None, "Am", 52, 71)
    nxt = lead(prev, "F", 52, 71)
    moved = sum(min(abs(a - b) for b in prev) for a in nxt)
    ok &= check(moved <= 3, f"Am {prev} -> F {nxt}: moves {moved} semitones")
    ok &= check(all(len(v) == 3 for v in close_voicings("C", 48, 72)), "close voicings")
    ok &= check(prog(["Am", "F"], 5) == ["Am", "F", "Am", "F", "Am"], "prog repeats")
    ex = Path(__file__).resolve().parents[1] / "example"
    film_path, words = (sys.argv[1], sys.argv[2]) if len(sys.argv) > 2 else (str(ex / "film.py"), str(ex / "words.json"))
    if film_path:
        sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
        spec = importlib.util.spec_from_file_location("film", film_path)
        film = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(film)
        W = Words(words)
        print(f"words: {len(W.W)}, ends {W.end():.2f} s")
        spans = []
        for bid, fn in film.BEDS.items():
            bed = fn(W)
            downs = [s for s, L, b in bed.clock.bars]
            for k, t in bed.anchors.items():
                ok &= check(min(abs(d - t) for d in downs + [bed.clock.end()]) < 1e-6, f"bed {bid}: {k} ({t:.3f}) on a downbeat")
            for k, (tn, t) in bed.events.items():
                tr = next(x for x in bed.tracks if x.name == tn)
                ok &= check(min(abs(n[0] - t) for n in tr.notes) < 0.005, f"bed {bid}: {k} on its word")
            notes = [n for tr in bed.tracks for n in tr.notes]
            ok &= check(all(0 <= n[2] + tr.transpose <= 127 for tr in bed.tracks for n in tr.notes), f"bed {bid}: {len(notes)} notes in range")
            spans.append((bed.t0, bed.t1, bid))
        spans.sort()
        for (a0, a1, a), (b0, b1, b) in zip(spans, spans[1:]):
            ok &= check(b0 >= a1 - 1e-6, f"beds {a} and {b} never play at once ({a} ends {a1:.3f}, {b} begins {b0:.3f})")
            if b0 > a1 + 0.05:
                print(f"  note {a1:.2f}-{b0:.2f} s has no bed: a designed silence goes in the cue sheet's SILENCES")
    print("ALL OK" if ok else "SOME CHECKS FAILED")
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
