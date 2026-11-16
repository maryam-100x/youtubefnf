"""A9 of the sound gate: where an interview bite (a clip of someone else speaking, played inside the narration) splits the narration.
A split on Whisper's end of a word sits before the word's own release (a t, a k), so the release plays after the clip, a stray sound
before the voice comes back. The split belongs inside the digital silence after the phrase; this check holds every split to that:
  CUT    the split point sits on sound: a 10-ms frame within 20 ms of it over -55 dB;
  LEFT   a short sound (under 0.2 s, over -45 dB) between the split and the next speech: the end of the word before, played after the
         clip.
Reads the narration's own seconds from <dj>/build/insert/inserts.json ({"name": {"at": ...}}); no inserts, nothing to check.
Splits placed in the silence after the phrase pass; the same splits at Whisper's word ends are flagged.

  EDIT tools/sound/insertcut.py <video> [--final F] [--at 178.88,267.2] [--json out]"""
import argparse
import json
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
import gatelib as G  # noqa: E402

HOP = 0.01
ON_SOUND = -55.0
LEFT_LOUD, LEFT_MAX = -45.0, 0.20
SPEECH = -30.0     # the next speech: 10 frames in a row over this


def check_split(db, name, at):
    i = int(round(at / HOP))
    near = db[max(0, i - 2):i + 2]
    if len(near) and near.max() > ON_SOUND:
        return G.flag("A9", f"cut:{name}", at, name, f"the split for the {name!r} bite at {at:.2f} s sits on sound "
                      f"({near.max():.0f} dB within 20 ms): split inside the silence after the phrase")
    j = i
    while j + 10 < len(db) and not (db[j:j + 10] > SPEECH).all():
        j += 1
    while j > i and db[j - 1] > ON_SOUND:      # the next speech's own onset ramp is the speech
        j -= 1
    k = i
    while k < j:
        if db[k] > LEFT_LOUD:
            e = k
            while e < j and db[e] > LEFT_LOUD - 10:
                e += 1
            if (e - k) * HOP < LEFT_MAX:
                return G.flag("A9", f"left:{name}", k * HOP, name, f"{(e - k) * HOP * 1000:.0f} ms of sound at {db[k:e].max():.0f} dB between "
                              f"the {name!r} split ({at:.2f} s) and the next speech: the end of the word before plays after the clip "
                              f"(a stray release before the voice); move the split past it")
            k = e
        k += 1
    return None


def run(P, quiet=False, ats=None):
    ins = Path(P["dj"]) / "build" / "insert" / "inserts.json"
    if ats:
        items = {f"at{i + 1}": float(a) for i, a in enumerate(ats)}
    elif ins.exists():
        items = {k: float(v["at"]) for k, v in json.loads(ins.read_text(encoding="utf-8")).items()}
    else:
        items = {}
    flags = []
    if items:
        x, sr = G.load_mono(P["final"])
        db = G.frame_db(x, sr, HOP)
        for name, at in items.items():
            f = check_split(db, name, at)
            if f:
                flags.append(f)
    res = {"check": "A9", "final": str(P["final"]), "inserts": items, "flags": flags}
    if not quiet:
        print(f"A9 insert splits: {len(items)} bites; {len(flags)} flags")
        G.print_flags(res)
    return res


def main():
    G.utf8_stdout()
    ap = G.add_path_args(argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter))
    ap.add_argument("--at", help="comma list of split times to check instead of inserts.json")
    a = ap.parse_args()
    res = run(G.paths_from(a), ats=a.at.split(",") if a.at else None)
    G.write_json(a.json, res)
    sys.exit(1 if res["flags"] else 0)


if __name__ == "__main__":
    main()
