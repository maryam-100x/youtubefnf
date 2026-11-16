"""Balance a bed from its stems without rendering again.

`music.py render ... --stems` (render_bed's stems=) writes one WAV per part. This mixes them with per-part gains through the bed's bus,
measures the result against the bar (bands.measure) and, with --judge, scores it; with --out it writes the bed (and copies the grid
from the first render, which a gain change doesn't move).

    SYNTH tools/music/music.py mixdown <stems dir> [part=gain_db ...] [--judge] [--out bed.wav --grid <rendered bed>.wav.grid.json]
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import soundfile as sf

from .bands import measure
from .compose import bus
from .settings import SR, ensure_parent


def main():
    args = list(sys.argv[1:])
    if not args or args[0] in ("-h", "--help"):
        raise SystemExit(__doc__)
    d = Path(args.pop(0))
    gains = dict((k, float(v)) for k, v in (a.split("=") for a in args if "=" in a and not a.startswith("--")))
    out = args[args.index("--out") + 1] if "--out" in args else None
    grid = args[args.index("--grid") + 1] if "--grid" in args else None
    stems = {p.stem: sf.read(p, dtype="float32", always_2d=True)[0].T for p in sorted(d.glob("*.wav"))}
    if not stems:
        raise SystemExit(f"no stems in {d}")
    n = max(a.shape[1] for a in stems.values())
    mix = np.zeros((2, n), np.float32)
    for k, a in stems.items():
        mix[:, :a.shape[1]] += a * (10 ** (gains.get(k, 0.0) / 20))
    mix = bus(mix)
    m = measure(mix)
    print("parts:", ", ".join(f"{k} {gains.get(k, 0.0):+.1f}" for k in stems), "|", m, flush=True)
    if "--judge" in args:
        from . import judge
        print("judge:", judge.score_array(mix.T, SR), flush=True)
    if out:
        sf.write(ensure_parent(out), mix.T, SR, subtype="PCM_24")
        meta = {"stems": str(d), "gains": gains, "measure": m}
        if grid:
            g = json.loads(Path(grid).read_text(encoding="utf-8"))
            g["file"] = Path(out).name
            Path(out + ".grid.json").write_text(json.dumps(g), encoding="utf-8")
            first = Path(str(grid)[:-len(".grid.json")] + ".json")   # the first render's metadata: its film span
            if first.exists():
                fm = json.loads(first.read_text(encoding="utf-8"))
                meta.update({k: fm[k] for k in ("t0", "t1", "sr", "tracks", "shaping") if k in fm})
        Path(out + ".json").write_text(json.dumps(meta, indent=1), encoding="utf-8")
        print("->", out)


if __name__ == "__main__":
    main()
