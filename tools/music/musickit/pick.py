"""Choose each part's sound in context, by the stand-in ear.

A sound is chosen by how the whole bed scores with it: every candidate patch plays its real part of the bed, held at the part's set
level (patches differ by 20 dB+, so loudness can't win), mixed with the other parts' current picks through the bed's bus, then scored
by the quality model (judge.py: PQ + CE + CU) less penalties past the bar's spectrum (centroid over 760 Hz: 1 point per 200 Hz;
voice band over 1.5%: 0.5 point per %). The bar decides first: a candidate that puts the bed over the bar's 1.2% in 1-4 kHz loses to
every candidate inside it, whatever its value. One part at a time: the winner is kept, then the next part is picked against it.

    SYNTH tools/music/music.py pick <film.py> <bed id> <t0> <t1> <cands.json> <out.json> --words <words.json>

    t0, t1: the film window to judge (20-30 s of the bed that has every part playing)
    cands.json: {"order": ["pad", "pulse", ...],
                 "<track name>": {"base": "<patch>", "cands": ["<patch>", "<patch>@-12", ...]}, ...}
                "@-12" plays the candidate an octave down (try it for anything that lands in the voice band)
    Tracks cands.json doesn't name are left out of the excerpt.

Afterwards: put the winners in the film's KIT (writing.KIT or a film-level override), run `music.py check` on each (octave, added
tones), render the bed and check it at the bar (`music.py bands --judge`). The log in out.json keeps every candidate's numbers: that is the record of
why each sound won.
"""
from __future__ import annotations

import importlib.util
import json
import sys
import time
from pathlib import Path

import numpy as np

from . import judge
from .bands import BAR
from .compose import LEVELS, bus, render_track
from .settings import SR, ensure_parent
from .surge import Surge
from .writing import Words


def spectrum(mix: np.ndarray) -> tuple[float, float]:
    m = mix.mean(0)
    S = np.abs(np.fft.rfft(m * np.hanning(len(m)))) ** 2
    f = np.fft.rfftfreq(len(m), 1 / SR)
    tot = S.sum() + 1e-12
    return float((f * S).sum() / tot), float(S[(f >= 1000) & (f < 4000)].sum() / tot * 100)


def value(sc: dict, cen: float, vb: float) -> float:
    pen = max(0.0, cen - 760) / 200 + max(0.0, vb - 1.5) * 0.5
    return sc["PQ"] + sc["CE"] + sc["CU"] - pen


def load_film(path: str):
    spec = importlib.util.spec_from_file_location("film", path)
    mod = importlib.util.module_from_spec(spec)
    sys.path.insert(0, str(Path(path).resolve().parent))
    spec.loader.exec_module(mod)
    return mod


def main():
    args = sys.argv[1:]
    if len([a for a in args if not a.startswith("--")]) < 6:
        raise SystemExit(__doc__)
    words = args[args.index("--words") + 1] if "--words" in args else None
    pos = [a for i, a in enumerate(args) if not a.startswith("--") and (i == 0 or args[i - 1] != "--words")]
    film_path, bed_id, t0, t1, cands_path, out_path = pos[:6]
    t0, t1 = float(t0), float(t1)
    film = load_film(film_path)
    W = Words(words or (Path(film_path).resolve().parent / film.DEFAULT_WORDS))
    C = json.loads(Path(cands_path).read_text(encoding="utf-8"))
    ensure_parent(out_path)
    bed = film.BEDS[bed_id](W)
    tracks = [t for t in bed.tracks if t.name in C]
    for t in tracks:
        name, _, tp = C[t.name]["base"].partition("@")
        t.patch, t.transpose = name, int(tp or 0)
        t.level = LEVELS.get(t.name, -26.0)
        t.gain_db = 0.0
    secs = t1 - t0
    s = Surge(sr=SR)
    cache: dict = {}

    def stem(tr, patch):
        """`patch` may carry a transposition: 'Plucks/X@-24' plays every note two octaves down."""
        key = (tr.name, patch)
        if key not in cache:
            old, old_tp = tr.patch, tr.transpose
            name, _, tp = patch.partition("@")
            tr.patch, tr.transpose = name, int(tp or 0)
            try:
                cache[key] = render_track(s, tr, t0, t1, secs)
            except Exception as e:  # a patch that won't load scores nothing
                print(f"   ! {patch}: {str(e)[:120]}", flush=True)
                cache[key] = None
            tr.patch, tr.transpose = old, old_tp
        return cache[key]

    picked = {t.name: C[t.name]["base"] for t in tracks}
    log = {"film": film_path, "bed": bed_id, "t0": t0, "t1": t1, "rounds": []}
    started = time.time()
    for role in C.get("order", [t.name for t in tracks]):
        tr = next(t for t in tracks if t.name == role)
        rows = []
        for patch in [C[role]["base"]] + [c for c in C[role]["cands"] if c != C[role]["base"]]:
            parts = []
            for t in tracks:
                a = stem(t, patch if t.name == role else picked[t.name])
                if a is not None:
                    parts.append(a)
            if stem(tr, patch) is None:
                continue
            mix = bus(np.sum(parts, axis=0))
            cen, vb = spectrum(mix)
            sc = judge.score_array(mix.T, SR)
            v = value(sc, cen, vb)
            rows.append({"patch": patch, "value": round(v, 3), "PQ": sc["PQ"], "CE": sc["CE"], "CU": sc["CU"], "PC": sc["PC"],
                         "centroid": round(cen), "voice_band": round(vb, 2)})
            print(f"{role:6s} {patch[:44]:44s} val {v:6.2f} PQ {sc['PQ']:.2f} CE {sc['CE']:.2f} CU {sc['CU']:.2f} cen {cen:5.0f} "
                  f"vb {vb:4.2f}  [{time.time() - started:4.0f}s]", flush=True)
        rows.sort(key=lambda r: (r["voice_band"] > BAR["voice_band"], -r["value"]))   # inside the bar first, then the value
        picked[role] = rows[0]["patch"]
        name, _, tp = picked[role].partition("@")
        tr.patch, tr.transpose = name, int(tp or 0)
        log["rounds"].append({"role": role, "picked": picked[role], "rows": rows})
        print(f"== {role}: {picked[role]} ({rows[0]['value']:.2f})", flush=True)
        Path(out_path).write_text(json.dumps({**log, "picked": picked}, indent=1), encoding="utf-8")
    print("picked:", json.dumps(picked, indent=1))


if __name__ == "__main__":
    main()
